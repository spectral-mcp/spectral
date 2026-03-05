# First analysis

This guide turns a capture bundle into an API specification.

## Run the analysis

Pass the app name to the `openapi analyze` command with an output base name:

```bash
uv run spectral openapi analyze myapp -o myapp-api
```

For GraphQL captures, use `spectral graphql analyze` instead. The command loads all captures for the app, merges them into a single bundle, and produces the appropriate output files.

## What happens during analysis

The pipeline runs several steps, printing progress along the way:

1. **Load** — Loads and merges all captures for the app, reports trace, WebSocket, and context counts
2. **Extract pairs** — Collects all observed (method, URL) pairs from the traces
3. **Detect base URL** — The LLM identifies the business API origin, filtering out CDN, analytics, and tracker domains
4. **Filter** — Keeps only the traces that match the detected base URL
5. **Protocol split** — Separates REST and GraphQL traces
6. **Extraction** — Builds endpoint patterns (REST) or reconstructs types (GraphQL) from the raw traces
6. **Enrichment** — Parallel LLM calls add business semantics: operation summaries, parameter descriptions, response explanations
7. **Assembly** — Combines everything into the final output files

Authentication analysis is a separate step, run via `spectral auth analyze`. See [Auth detection](../analyze/auth-detection.md) for details.

## Output files

Each analyze command produces output specific to its protocol:

| Command | File | Contents |
|---------|------|----------|
| `openapi analyze` | `<name>.yaml` | OpenAPI 3.1 specification |
| `openapi analyze` | `<name>.restish.json` | Restish configuration entry for this API |
| `graphql analyze` | `<name>.graphql` | SDL schema with type descriptions |

## Options

Skip the LLM enrichment step to get a faster but less detailed spec:

```bash
uv run spectral openapi analyze myapp -o myapp-api --skip-enrich
```

Use a different model:

```bash
uv run spectral openapi analyze myapp -o myapp-api --model claude-sonnet-4-5-20250929
```

Save all LLM prompts and responses for inspection:

```bash
uv run spectral openapi analyze myapp -o myapp-api --debug
```

See [Debug mode](../analyze/debug-mode.md) for details on reading the debug output.

## Next steps

- [Calling the API](calling-the-api.md) — use the generated spec and Restish config to make API calls
- [REST output](../analyze/rest-output.md) — understand the OpenAPI spec in detail
- [GraphQL output](../analyze/graphql-output.md) — understand the SDL schema in detail
