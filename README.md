<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/banner-wide-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/banner-wide-light.png">
    <img src="assets/banner-wide-dark.png" alt="Spectral" width="600">
  </picture>
</p>

<p align="center">
  <a href="https://romain-gilliotte.github.io/spectral/getting-started/installation/"><strong>Getting started</strong></a> &nbsp;&bull;&nbsp;
  <a href="https://romain-gilliotte.github.io/spectral/reference/cli/"><strong>CLI reference</strong></a> &nbsp;&bull;&nbsp;
  <a href="https://romain-gilliotte.github.io/spectral/"><strong>Full documentation</strong></a>
</p>

Turn any app into an API that Claude can use. Browse normally, Spectral figures out the API, then AI agents call it directly.

Want Claude to pay for your parking, pull numbers from your accounting software, or search listings on your city's classifieds site — without brittle browser automation? Most apps sit on undocumented APIs that work perfectly well. Spectral captures the traffic, has an LLM figure out what each call means, and turns it into tools that Claude can call.

MCP tools work with any HTTP/JSON API regardless of protocol. Spectral can also generate formal API specs — OpenAPI 3.1 for REST APIs, SDL schemas for GraphQL — for human consumption and code generation.

## How it works

1. **Capture** — Chrome extension (web) or MITM proxy records traffic + UI actions while you browse
2. **Analyze** — LLM correlates UI actions with API calls, infers endpoint patterns, auth flow, and business meaning
3. **Use** — Start the MCP server. Claude calls the API directly, with auth handled automatically

## Quick start

Prerequisites: Python 3.11+, [uv](https://docs.astral.sh/uv/), [Anthropic API key](https://console.anthropic.com/).

```bash
git clone https://github.com/romain-gilliotte/spectral.git && cd spectral
uv sync
```

Set up the Chrome extension and capture traffic:

```bash
# Load extension/ as unpacked in chrome://extensions, then connect it:
uv run spectral extension install --extension-id <id-from-chrome-extensions>

# Chrome extension: Start Capture → browse → Stop Capture → Send to Spectral
# Or use the MITM proxy (stores directly):
uv run spectral capture proxy -a myapp
```

Analyze captures, set up auth, and start the MCP server:

```bash
uv run spectral mcp analyze myapp                      # → MCP tool definitions
uv run spectral auth analyze myapp                     # → auth script (acquire/refresh tokens)
uv run spectral auth login myapp                       # interactive login
uv run spectral mcp stdio                              # start MCP server for AI agents
```

Or generate API specs (REST/GraphQL only):

```bash
uv run spectral openapi analyze myapp -o myapp-api    # → myapp-api.yaml (OpenAPI 3.1)
uv run spectral graphql analyze myapp -o myapp-api     # → myapp-api.graphql (SDL schema)
```

## Capture methods

| Method                                                                                            | Best for                | UI context                             | Needs certification installation                                                            |
| ------------------------------------------------------------------------------------------------- | ----------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------- |
| [Chrome extension](https://romain-gilliotte.github.io/spectral/capture/chrome-extension/)         | Web apps                | Yes — clicks, navigation, page content | No                                                                                          |
| [MITM proxy](https://romain-gilliotte.github.io/spectral/capture/mitm-proxy/)                     | CLI tools, desktop apps | No                                     | Yes — [setup guide](https://romain-gilliotte.github.io/spectral/capture/certificate-setup/) |
| [Android APK patching + MITM proxy](https://romain-gilliotte.github.io/spectral/capture/android/) | Mobile apps             | No                                     | Yes — [setup guide](https://romain-gilliotte.github.io/spectral/capture/certificate-setup/) |

## Documentation

| Guide                                                                                           | Description                                    |
| ----------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| [Installation](https://romain-gilliotte.github.io/spectral/getting-started/installation/)       | Setup: CLI, Chrome extension, native messaging |
| [First capture](https://romain-gilliotte.github.io/spectral/getting-started/first-capture/)     | Record traffic from a web app or mobile app    |
| [First analysis](https://romain-gilliotte.github.io/spectral/getting-started/first-analysis/)   | Generate MCP tools from captured traffic       |
| [Calling the API](https://romain-gilliotte.github.io/spectral/getting-started/calling-the-api/) | Use the MCP server with Claude                 |
| [CLI reference](https://romain-gilliotte.github.io/spectral/reference/cli/)                     | All commands and options                       |
| [Auth detection](https://romain-gilliotte.github.io/spectral/analyze/auth-detection/)           | How Spectral handles authentication            |

## License

[MIT](LICENSE)
