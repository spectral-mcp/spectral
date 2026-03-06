"""Schema inference utilities.

All four parts of an endpoint (path params, query params, request body,
response body) use the same annotated JSON-schema format produced by
``infer_schema``.  The ``infer_path_schema`` and ``infer_query_schema``
helpers build schemas from trace URLs so that all four are uniform.
"""

from __future__ import annotations

from collections import defaultdict
import re
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

from cli.commands.capture.types import Trace
from cli.helpers.json.schema_inference import (
    collect_observed,
    detect_format,
    infer_schema,
    infer_type_from_values,
    merge_property_schemas,
)
import cli.helpers.llm as llm

# Re-export for convenience
__all__ = [
    "infer_schema",
    "infer_path_schema",
    "infer_query_schema",
    "resolve_map_candidates",
]


def _extract_path_param_values(
    traces: list[Trace],
    path_pattern: str,
    param_names: list[str],
) -> dict[str, list[str]]:
    """Extract observed path parameter values from trace URLs.

    Builds a named-group regex from the pattern and matches each trace URL
    to collect distinct values per parameter.
    """
    regex = path_pattern
    for name in param_names:
        regex = regex.replace(f"{{{name}}}", f"(?P<{name}>[^/]+)")
    regex = regex + "$"
    compiled = re.compile(regex)

    result: dict[str, list[str]] = {name: [] for name in param_names}
    seen: dict[str, set[str]] = {name: set() for name in param_names}
    for t in traces:
        parsed = urlparse(t.meta.request.url)
        m = compiled.search(parsed.path)
        if m:
            for name in param_names:
                val = m.group(name)
                if val and val not in seen[name]:
                    seen[name].add(val)
                    result[name].append(val)
    return result


def infer_path_schema(
    traces: list[Trace], path_pattern: str
) -> dict[str, Any] | None:
    """Infer an annotated JSON schema for path parameters.

    Extracts parameter values from trace URLs using the path pattern, then
    builds a schema in the same format as ``infer_schema``: an object with
    one property per path parameter, each carrying type, optional format,
    and observed values.  All path parameters are required.

    Returns ``None`` when the pattern contains no ``{param}`` segments.
    """
    param_names = re.findall(r"\{(\w+)\}", path_pattern)
    if not param_names:
        return None

    observed = _extract_path_param_values(traces, path_pattern, param_names)

    properties: dict[str, Any] = {}
    for name in param_names:
        values = observed.get(name, [])
        ptype = infer_type_from_values(values) if values else "string"
        prop: dict[str, Any] = {"type": ptype}
        if ptype == "string" and values:
            fmt = detect_format(values)
            if fmt:
                prop["format"] = fmt
        prop["observed"] = collect_observed(values)
        properties[name] = prop

    return {
        "type": "object",
        "properties": properties,
        "required": list(param_names),
    }


def infer_query_schema(traces: list[Trace]) -> dict[str, Any] | None:
    """Infer an annotated JSON schema for query string parameters.

    Collects query-string values across all *traces*, infers type and
    format per parameter.  Returns the same annotated-schema format as
    ``infer_schema``.

    Returns ``None`` when no query parameters are found.
    """
    raw_params: dict[str, list[str]] = defaultdict(list)
    for trace in traces:
        parsed = urlparse(trace.meta.request.url)
        qs = parse_qs(parsed.query)
        for key, values in qs.items():
            raw_params[key].extend(values)

    if not raw_params:
        return None

    properties: dict[str, Any] = {}
    for name, values in raw_params.items():
        ptype = infer_type_from_values(values)
        prop: dict[str, Any] = {"type": ptype}
        if ptype == "string" and values:
            fmt = detect_format(values)
            if fmt:
                prop["format"] = fmt
        prop["observed"] = collect_observed(values)
        properties[name] = prop

    return {"type": "object", "properties": properties}


# ---------------------------------------------------------------------------
# LLM-based map candidate resolution
# ---------------------------------------------------------------------------


def _collect_map_candidates(
    schema: dict[str, Any], path: str = ""
) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """Walk *schema* recursively, returning ``(path, parent, candidate)`` tuples.

    Each tuple contains the dotted path to the annotated node, a reference to
    the node itself (so it can be mutated in-place), and the ``x-map-candidate``
    dict.
    """
    results: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    candidate: dict[str, Any] | None = schema.get("x-map-candidate")  # pyright: ignore[reportAssignmentType]
    if isinstance(candidate, dict):
        results.append((path or "(root)", schema, candidate))

    # Recurse into properties
    for key, prop in schema.get("properties", {}).items():
        if isinstance(prop, dict):
            child_path = f"{path}.{key}" if path else key
            results.extend(_collect_map_candidates(cast(dict[str, Any], prop), child_path))

    # Recurse into additionalProperties
    addl: dict[str, Any] | None = schema.get("additionalProperties")  # pyright: ignore[reportAssignmentType]
    if isinstance(addl, dict):
        child_path = f"{path}[*]" if path else "[*]"
        results.extend(_collect_map_candidates(addl, child_path))

    # Recurse into array items
    items_val: dict[str, Any] | None = schema.get("items")  # pyright: ignore[reportAssignmentType]
    if isinstance(items_val, dict):
        child_path = f"{path}[]" if path else "[]"
        results.extend(_collect_map_candidates(items_val, child_path))

    return results


async def resolve_map_candidates(schemas: list[dict[str, Any]]) -> None:
    """Resolve ``x-map-candidate`` annotations via one batched LLM call.

    Walks all *schemas* (mutating them in-place), collects every
    ``x-map-candidate`` annotation, and asks the LLM whether each group of
    keys represents a dynamic map or fixed properties.  Confirmed maps are
    collapsed to ``additionalProperties``; denied candidates keep their
    ``properties`` unchanged.

    Skips the LLM call entirely when no candidates are found.
    """
    all_candidates: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for schema in schemas:
        all_candidates.extend(_collect_map_candidates(schema))

    if not all_candidates:
        return

    # Build a compact prompt with one group per candidate.
    groups: list[str] = []
    for i, (_path, _node, candidate) in enumerate(all_candidates, 1):
        keys_str = ", ".join(f'"{k}"' for k in candidate["keys"])
        shared_str = ", ".join(candidate["shared_properties"])
        extra_str = ", ".join(candidate["extra_properties"]) or "(none)"
        groups.append(
            f"Group {i}:\n"
            f"  keys: [{keys_str}]\n"
            f"  shared properties: [{shared_str}]\n"
            f"  extra properties: [{extra_str}]"
        )

    prompt = (
        "For each group below, determine whether the keys are dynamic IDs "
        "(a map/dictionary where each key is a unique identifier) or fixed "
        "property names.\n\n"
        + "\n\n".join(groups)
        + "\n\nRespond as a JSON array: "
        '[{"group": 1, "is_map": true}, ...]'
    )

    raw = await llm.ask(prompt, label="resolve-map-candidates")
    parsed = llm.extract_json(raw)
    decisions: list[dict[str, Any]] = parsed if isinstance(parsed, list) else [parsed]

    decision_map: dict[int, bool] = {}
    for d in decisions:
        gnum = d.get("group")
        is_map = d.get("is_map")
        if isinstance(gnum, int) and isinstance(is_map, bool):
            decision_map[gnum] = is_map

    for i, (_path, node, candidate) in enumerate(all_candidates, 1):
        is_map = decision_map.get(i)
        if is_map is True:
            # Collapse properties into additionalProperties.
            props = node.get("properties", {})
            all_values: list[Any] = []
            for prop_schema in props.values():
                all_values.append(prop_schema)
            value_schema = merge_property_schemas(all_values) if all_values else {}
            node.pop("properties", None)
            node["additionalProperties"] = value_schema
            node["x-key-pattern"] = "dynamic"
            node["x-key-examples"] = candidate["keys"][:5]
        # Always remove the temporary annotation.
        node.pop("x-map-candidate", None)
