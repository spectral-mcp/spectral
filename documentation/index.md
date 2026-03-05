# Spectral

Turn any app into an API that AI agents can call. Browse normally, Spectral figures out the API, then Claude calls it directly — no browser automation needed.

Want an AI agent that pays for your parking, pulls numbers from your accounting software, or searches listings on a classifieds site? Most apps sit on undocumented APIs that work perfectly well, but without tooling, you're stuck with Playwright, Selenium, or Puppeteer: slow, fragile, breaks on every UI change, can't handle mobile. Spectral captures the traffic, has an LLM figure out what each call means, and produces tools that Claude can use.

## How it works

Spectral is a three-stage pipeline:

1. **Capture** — A Chrome extension or MITM proxy records network traffic and UI actions while you browse the app normally. Captures are imported into managed storage, where multiple sessions for the same app can be accumulated and merged.

2. **Analyze** — A CLI tool loads all captures for an app, merges them, then correlates what you clicked with what the app sent over the network, using an LLM to understand the business meaning of each API call.

3. **Use** — Start the MCP server. Claude calls the API directly, with auth handled automatically.

The key innovation is the correlation of UI actions with network traffic. Instead of just recording technical shapes, Spectral understands *why* each API call exists — what business operation it represents, what the parameters mean, how authentication works.

## What you get

| Output | Command | Contents |
|--------|---------|----------|
| MCP tools | `mcp analyze` | Tool definitions for any HTTP/JSON API — AI agents call them directly via `mcp stdio` |
| Auth script | `auth analyze` | Token acquisition and refresh logic, stored in managed storage |
| OpenAPI 3.1 YAML | `openapi analyze` | Endpoint patterns, request/response schemas, business descriptions (REST APIs only) |
| SDL schema | `graphql analyze` | Reconstructed types with field descriptions, nullability, and list cardinality (GraphQL APIs only) |

All formats include LLM-inferred business semantics that a purely mechanical tool could not produce: operation summaries, parameter descriptions, and authentication flow documentation.

## Next steps

- [Installation](getting-started/installation.md) — set up Spectral on your machine
- [First capture](getting-started/first-capture.md) — record traffic from a web app
- [First analysis](getting-started/first-analysis.md) — turn a capture into MCP tools or an API spec
- [Calling the API](getting-started/calling-the-api.md) — use MCP tools or curl to call the API
