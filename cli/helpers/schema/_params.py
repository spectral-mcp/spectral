"""Path parameter schema inference."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from cli.commands.capture.types import Trace
from cli.helpers.schema._scalars import coerce_value
from cli.helpers.schema._schema_inference import infer_schema


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


def _build_samples(
    observed: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Zip per-param value lists into sample dicts with coerced values.

    Each sample dict maps parameter names to coerced Python values.  The
    number of samples equals the length of the longest value list; shorter
    lists are padded by repeating the last value.
    """
    if not observed:
        return []
    max_len = max(len(vals) for vals in observed.values())
    if max_len == 0:
        return []
    samples: list[dict[str, Any]] = []
    for i in range(max_len):
        sample: dict[str, Any] = {}
        for name, vals in observed.items():
            raw = vals[i] if i < len(vals) else vals[-1]
            sample[name] = coerce_value(raw)
        samples.append(sample)
    return samples


def infer_path_schema(traces: list[Trace], path_pattern: str) -> dict[str, Any] | None:
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
    samples = _build_samples(observed)
    schema = (
        infer_schema(samples)
        if samples
        else infer_schema([{name: "" for name in param_names}])
    )
    schema["required"] = list(param_names)
    return schema
