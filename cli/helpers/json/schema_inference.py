"""Pure JSON schema inference from object samples.

No domain types — operates solely on ``list[dict[str, Any]]`` inputs.
"""

from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

# (name, regex, min_keys) — high-confidence patterns (uuid, hex) need only 1 key;
# ambiguous patterns (date, year, numeric) need 3 to avoid false positives.
_DYNAMIC_KEY_PATTERNS: list[tuple[str, re.Pattern[str], int]] = [
    ("date", re.compile(r"^\d{4}-\d{2}-\d{2}"), 3),
    ("year-month", re.compile(r"^\d{4}-\d{2}$"), 3),
    ("uuid", re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I), 1),
    ("prefixed-uuid", re.compile(r"^.+-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I), 1),
    ("year", re.compile(r"^(?:19|20)\d{2}$"), 3),
    ("numeric-id", re.compile(r"^\d+$"), 3),
    ("hex-id", re.compile(r"^[0-9a-f]{20,}$", re.I), 1),
]

_MIN_STRUCTURAL_KEYS = 5


def _classify_key_pattern(keys: list[str]) -> str | None:
    """Return the pattern name if ALL *keys* match a single dynamic pattern.

    Each pattern carries its own minimum key count.  High-confidence patterns
    (UUID, hex hash) trigger with a single key; ambiguous patterns (date,
    numeric) require at least 3.  Returns ``None`` when no pattern matches.
    """
    for name, regex, min_keys in _DYNAMIC_KEY_PATTERNS:
        if len(keys) >= min_keys and all(regex.search(k) for k in keys):
            return name
    return None


def _schemas_structurally_similar(value_dicts: list[dict[str, Any]]) -> bool:
    """Return True when all *value_dicts* are objects with >50% property overlap.

    Each element must be a ``dict`` with at least one key.  Overlap is measured
    via the Jaccard index: ``|intersection| / |union|`` of the property-name
    sets across all dicts.
    """
    if not value_dicts:
        return False
    sets = [set(d.keys()) for d in value_dicts]
    intersection = sets[0]
    union = sets[0]
    for s in sets[1:]:
        intersection = intersection & s
        union = union | s
    if not union:
        return False
    return len(intersection) / len(union) > 0.5


def infer_type(value: Any) -> str:
    """Infer JSON schema type from a Python value."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def infer_type_from_values(values: list[str]) -> str:
    """Infer type from a list of string values."""
    if all(v.isdigit() for v in values if v):
        return "integer"
    if all(_is_float(v) for v in values if v):
        return "number"
    if all(v.lower() in ("true", "false") for v in values if v):
        return "boolean"
    return "string"


def _is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def detect_format(values: list[Any]) -> str | None:
    """Detect common string formats."""
    str_values = [v for v in values if isinstance(v, str)]
    if not str_values:
        return None

    if all(re.match(r"^\d{4}-\d{2}-\d{2}", v) for v in str_values):
        return "date-time" if any("T" in v for v in str_values) else "date"

    if all(re.match(r"^[^@]+@[^@]+\.[^@]+$", v) for v in str_values):
        return "email"

    if all(
        re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", v, re.I
        )
        for v in str_values
    ):
        return "uuid"

    if all(re.match(r"^https?://", v) for v in str_values):
        return "uri"

    return None


def collect_observed(values: list[Any], max_count: int = 5) -> list[Any]:
    """Collect up to *max_count* distinct observed values."""
    seen: list[Any] = []
    seen_set: set[str | int | float | bool | None] = set()
    for v in values:
        try:
            hashable: str | int | float | bool | None = (
                v if not isinstance(v, (dict, list)) else str(v)  # pyright: ignore[reportUnknownArgumentType]
            )
            if hashable not in seen_set:
                seen_set.add(hashable)
                seen.append(v)
                if len(seen) >= max_count:
                    break
        except TypeError:
            seen.append(v)
            if len(seen) >= max_count:
                break
    return seen


def infer_schema(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Infer a JSON schema from multiple object samples, annotated with observed values.

    Recursively explores nested objects and arrays of objects so that the
    resulting schema fully describes the structure at every level.

    Each property carries its type, optional format, and an "observed" list of up
    to 5 distinct values seen across samples.

    Returns a dict like:
    {
        "type": "object",
        "properties": {
            "status": {"type": "string", "observed": ["active", "inactive"]},
            "count": {"type": "integer", "observed": [1, 5, 10]},
            "address": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "observed": ["Paris"]}
                }
            }
        }
    }
    """
    return _infer_object_schema(samples)


def _infer_object_schema(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Infer schema for a list of object samples (recursive)."""
    all_keys: dict[str, list[Any]] = defaultdict(list)
    for sample in samples:
        for key, value in sample.items():
            all_keys[key].append(value)

    # Check for dynamic map keys (dates, years, UUIDs, numeric IDs).
    pattern = _classify_key_pattern(list(all_keys.keys()))
    if pattern is not None:
        # Verify value type uniformity (all non-null values share the same type).
        all_values: list[Any] = []
        for vals in all_keys.values():
            all_values.extend(vals)
        non_null_values = [v for v in all_values if v is not None]
        if non_null_values:
            types = {infer_type(v) for v in non_null_values}
            if len(types) == 1:
                value_schema = _infer_property(all_values)
                sample_keys = list(all_keys.keys())[:5]
                return {
                    "type": "object",
                    "additionalProperties": value_schema,
                    "x-key-pattern": pattern,
                    "x-key-examples": sample_keys,
                }

    properties: dict[str, Any] = {}
    for key, values in all_keys.items():
        properties[key] = _infer_property(values)

    schema: dict[str, Any] = {"type": "object", "properties": properties}

    if pattern is None:
        candidate = _detect_map_candidate(all_keys)
        if candidate is not None:
            schema["x-map-candidate"] = candidate

    return schema


def _detect_map_candidate(
    all_keys: dict[str, list[Any]],
) -> dict[str, Any] | None:
    """Detect a structural map candidate when regex-based detection missed.

    Returns an ``x-map-candidate`` annotation dict when the object has
    ``_MIN_STRUCTURAL_KEYS`` or more keys whose non-null values are all
    dicts with >50% property overlap.  Returns ``None`` otherwise.
    """
    keys = list(all_keys.keys())
    if len(keys) < _MIN_STRUCTURAL_KEYS:
        return None

    value_dicts: list[dict[str, Any]] = []
    for vals in all_keys.values():
        non_null: list[Any] = [v for v in vals if v is not None]
        if not non_null or not all(isinstance(v, dict) and v for v in non_null):  # pyright: ignore[reportUnknownArgumentType]
            return None
        value_dicts.extend(v for v in non_null if isinstance(v, dict))  # pyright: ignore[reportUnknownArgumentType]

    if not value_dicts or not _schemas_structurally_similar(value_dicts):
        return None

    sets = [set(d.keys()) for d in value_dicts]
    intersection = sets[0]
    union = sets[0]
    for s in sets[1:]:
        intersection = intersection & s
        union = union | s

    return {
        "keys": keys[:10],
        "shared_properties": sorted(intersection),
        "extra_properties": sorted(union - intersection),
    }


def _infer_property(values: list[Any]) -> dict[str, Any]:
    """Infer schema for a single property from its observed values."""
    # Skip None values when determining the type so that a leading null
    # doesn't shadow the real type (e.g. [None, {"lon": 4.8}] → object).
    non_null = [v for v in values if v is not None]
    representative = non_null[0] if non_null else None
    prop_type = infer_type(representative)
    prop: dict[str, Any] = {"type": prop_type}

    if prop_type == "string" and non_null:
        fmt = detect_format(non_null)
        if fmt:
            prop["format"] = fmt

    if prop_type == "object":
        # Recurse into nested objects
        dict_values: list[dict[str, Any]] = [v for v in non_null if isinstance(v, dict)]
        if dict_values:
            nested = _infer_object_schema(dict_values)
            for k, v in nested.items():
                if k != "type":
                    prop[k] = v

    if prop_type == "array":
        # Infer items schema from array contents — observed goes on items, not here
        items_schema = _infer_array_items(non_null)
        if items_schema:
            prop["items"] = items_schema
        return prop

    prop["observed"] = collect_observed(values)
    return prop


def _infer_array_items(array_values: list[Any]) -> dict[str, Any] | None:
    """Infer the items schema for an array property.

    Collects all elements from all observed arrays and infers a unified schema.
    """
    all_elements: list[Any] = []
    for v in array_values:
        if isinstance(v, list):
            all_elements.extend(v)  # pyright: ignore[reportUnknownArgumentType]

    if not all_elements:
        return None

    # If all elements are objects, recurse
    dict_elements: list[dict[str, Any]] = [e for e in all_elements if isinstance(e, dict)]
    if dict_elements and len(dict_elements) == len(all_elements):
        return _infer_object_schema(dict_elements)

    # Otherwise infer a scalar type from the first element
    item_type = infer_type(all_elements[0])
    schema: dict[str, Any] = {"type": item_type}
    if item_type == "string":
        fmt = detect_format(all_elements)
        if fmt:
            schema["format"] = fmt
    schema["observed"] = collect_observed(all_elements)
    return schema


def merge_property_schemas(schemas: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple property schemas (from different map values) into one.

    Collects all nested ``properties`` into a union and delegates to
    ``_infer_property`` for each.  Falls back to the first schema if the
    inputs are not objects.
    """
    # If any schema has "properties", merge them as objects.
    all_have_props = all("properties" in s for s in schemas)
    if all_have_props:
        merged_keys: dict[str, list[Any]] = defaultdict(list)
        for s in schemas:
            for key, prop in s.get("properties", {}).items():
                merged_keys[key].append(prop)
        merged_props: dict[str, Any] = {}
        for key, prop_list in merged_keys.items():
            # Use the first schema as representative (they share structure).
            merged_props[key] = prop_list[0]
        result: dict[str, Any] = {"type": "object", "properties": merged_props}
        # Carry over observed if present on any input.
        for s in schemas:
            if "observed" in s:
                result["observed"] = s["observed"]
                break
        return result
    return schemas[0] if schemas else {}
