# Calling the API

After analyzing your captures, you have an API spec and can start making calls. This guide covers three approaches: MCP tools for AI agents, Restish for REST command-line use, and curl for manual requests.

## Authentication setup

Before calling the API, set up authentication. Spectral provides two paths depending on your situation.

### Generated auth script

If the app uses an interactive login flow (username/password, OAuth, OTP), generate an auth script and use it to log in:

```bash
uv run spectral auth analyze myapp
uv run spectral auth login myapp
```

The `auth analyze` command examines all captures for auth-related patterns and generates an `auth_acquire.py` script in managed storage. The `auth login` command runs that script, prompts for credentials, and stores the resulting token in `token.json`.

When the token expires, refresh it or log in again:

```bash
uv run spectral auth refresh myapp    # if a refresh endpoint was detected
uv run spectral auth login myapp      # re-authenticate from scratch
```

### Manual token injection

If the generated auth script does not work, or you already have a token, inject it directly:

```bash
uv run spectral auth set myapp -H "Authorization: Bearer eyJ..."
uv run spectral auth set myapp -c "session=abc123"
```

If neither `--header` nor `--cookie` is given, the command prompts for a token interactively.

To clear stored credentials:

```bash
uv run spectral auth logout myapp
```

## MCP tools (AI agents)

The primary way to use a discovered API is through MCP tools, which let AI agents call the API directly.

Generate tool definitions from captures:

```bash
uv run spectral mcp analyze myapp
```

This writes tool definitions to managed storage. Start the MCP server to expose them:

```bash
uv run spectral mcp stdio
```

Configure this command in your MCP client (Claude Desktop, Claude Code, etc.) as the stdio transport. The server exposes all app tools from managed storage, and handles authentication automatically using the stored token.

## REST APIs with Restish

### Install Restish

[Restish](https://rest.sh/) is a CLI for interacting with REST APIs. It understands OpenAPI specs and provides tab completion and human-readable output.

### Load the configuration

The `openapi analyze` command produces a `<name>.restish.json` file containing a single API entry. Merge it into your Restish configuration:

```bash
restish api edit < myapp-api.restish.json
```

Alternatively, copy the entry manually into `~/.config/restish/apis.json`.

### Make a call

Once the API is registered, Restish discovers all operations from the OpenAPI spec:

```bash
restish myapp-api --help
restish myapp-api get-user-profile
```

### Static auth with Restish

If the generated Restish config contains placeholder values like `<TOKEN>` or `<API_KEY>`, replace them with actual credentials. Edit the configuration at any time with `restish api edit myapp-api`.

## GraphQL APIs with curl

GraphQL output is a `.graphql` SDL schema file. Use the stored token with curl or any GraphQL client:

```bash
curl -X POST https://api.example.com/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"query": "{ viewer { name } }"}'
```

The token value can be found in the app's `token.json` in managed storage, or use MCP tools which handle authentication automatically.

## Troubleshooting

If a call returns an authentication error (401 or 403), the token may have expired. Force re-authentication:

```bash
uv run spectral auth refresh myapp    # try refresh first
uv run spectral auth login myapp      # or re-authenticate
uv run spectral auth logout myapp     # clear and start over
```
