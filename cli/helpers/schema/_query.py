"""Query parameter schema inference."""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from urllib.parse import parse_qs, urlparse

from cli.commands.capture.types import Trace
from cli.helpers.schema._scalars import coerce_value
from cli.helpers.schema._schema_inference import infer_schema


def infer_query_schema(traces: list[Trace]) -> dict[str, Any] | None:
    """Infer an annotated JSON schema for query string parameters.

    Collects query-string values across all *traces*, infers type and
    format per parameter.  Returns the same annotated-schema format as
    ``infer_schema``.

    Returns ``None`` when no query parameters are found.
    """
    # Collect raw string values per query parameter across all traces.
    raw_params: dict[str, list[str]] = defaultdict(list)
    for trace in traces:
        parsed = urlparse(trace.meta.request.url)
        qs = parse_qs(parsed.query)
        for key, values in qs.items():
            raw_params[key].extend(values)

    if not raw_params:
        return None

    # Build one sample dict per trace, coercing string values to Python types.
    samples: list[dict[str, Any]] = []
    for trace in traces:
        parsed = urlparse(trace.meta.request.url)
        qs = parse_qs(parsed.query)
        if qs:
            sample: dict[str, Any] = {}
            for key, values in qs.items():
                sample[key] = coerce_value(values[0])
            samples.append(sample)

    if not samples:
        return None

    return infer_schema(samples)
