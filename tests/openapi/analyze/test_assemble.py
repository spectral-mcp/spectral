"""Tests for REST OpenAPI assembly."""
# pyright: reportPrivateUsage=false

from typing import Any

from cli.commands.openapi.analyze.assemble import assemble_openapi
from cli.commands.openapi.analyze.types import (
    EndpointSpec,
    RequestSpec,
    ResponseSpec,
    SpecComponents,
)


class TestOpenApiExamples:
    """Tests for examples appearing in OpenAPI output."""

    def _build_simple_openapi(
        self,
        endpoints: list[EndpointSpec],
    ) -> dict[str, Any]:
        components = SpecComponents(
            app_name="Test",
            source_filename="test.zip",
            base_url="https://api.example.com",
            endpoints=endpoints,
        )
        return assemble_openapi(components)

    def test_response_example_body(self):
        endpoint = EndpointSpec(
            id="get_users",
            path="/users",
            method="GET",
            responses=[
                ResponseSpec(
                    status=200,
                    schema_={
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    },
                    example_body={"name": "Alice"},
                ),
            ],
        )
        openapi = self._build_simple_openapi([endpoint])
        media = openapi["paths"]["/users"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]
        assert media["example"] == {"name": "Alice"}

    def test_response_no_example_body(self):
        endpoint = EndpointSpec(
            id="get_users",
            path="/users",
            method="GET",
            responses=[
                ResponseSpec(
                    status=200,
                    schema_={
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    },
                ),
            ],
        )
        openapi = self._build_simple_openapi([endpoint])
        media = openapi["paths"]["/users"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]
        assert "example" not in media

    def test_examples_in_response_schema(self):
        endpoint = EndpointSpec(
            id="get_users",
            path="/users",
            method="GET",
            responses=[
                ResponseSpec(
                    status=200,
                    schema_={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "examples": ["Alice"]},
                        },
                    },
                ),
            ],
        )
        openapi = self._build_simple_openapi([endpoint])
        schema = openapi["paths"]["/users"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert schema["properties"]["name"]["examples"] == ["Alice"]

    def test_query_param_schema_examples(self):
        endpoint = EndpointSpec(
            id="search",
            path="/search",
            method="GET",
            request=RequestSpec(
                query_schema={
                    "type": "object",
                    "properties": {
                        "q": {"type": "string", "examples": ["hello", "world"]},
                    },
                }
            ),
        )
        openapi = self._build_simple_openapi([endpoint])
        param = openapi["paths"]["/search"]["get"]["parameters"][0]
        assert param["name"] == "q"
        assert param["schema"]["examples"] == ["hello", "world"]

    def test_request_body_schema_examples(self):
        endpoint = EndpointSpec(
            id="create_order",
            path="/orders",
            method="POST",
            request=RequestSpec(
                content_type="application/json",
                body_schema={
                    "type": "object",
                    "properties": {
                        "quantity": {"type": "integer", "examples": [2, 5]},
                    },
                },
            ),
        )
        openapi = self._build_simple_openapi([endpoint])
        body_schema = openapi["paths"]["/orders"]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]
        assert body_schema["properties"]["quantity"]["examples"] == [2, 5]
