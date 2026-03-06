"""Generic JSON utilities: serialization, simplification, schema inference."""

from cli.helpers.json.schema_inference import infer_schema
from cli.helpers.json.serialization import compact, minified
from cli.helpers.json.simplification import truncate_json

__all__ = ["compact", "infer_schema", "minified", "truncate_json"]
