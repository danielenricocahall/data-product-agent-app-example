# data-product-agent-app-example

This project is managed with [uv](https://docs.astral.sh/uv/) and targets Python 3.13.

## Quick start

```bash
uv sync
uv run python -V
```

## Data Contract PoC

This PoC defines ad-agency themed data contracts in Pydantic, including:
- Field-level PII classification metadata
- Lineage metadata
- Usage policy rules

### Run API

```bash
uv run fastapi dev src/data_product_agent_app_example/app.py
```

Hydrate sample registry data once:

```bash
uv run python -m data_product_agent_app_example.hydrate_registry
```

### Endpoints

Registry API (`:8000`)
- `GET /health`
- `GET /products`
- `GET /products/{domain}/{name}/{version}`
- `PUT /products/{domain}/{name}/{version}`
- `GET /products/{domain}/{name}/{version}/capabilities/{capability_name}`

Mock MCP Server (`:9000`)
- `GET /health`
- `POST /mcp`

The agent runs separately from the API:

```bash
OPENAI_API_KEY=... REGISTRY_API_URL=http://localhost:8000 uv run python -m data_product_agent_app_example.agents "campaign-performance"
```

The agent uses the registry API URL to discover products/capabilities and inject runtime tools for invocation. For MCP-backed capabilities, add `--autoload-mcp-tools` to dynamically load MCP tools using `MultiServerMCPClient`.

### Chat Terminal

Run local terminal chat:

```bash
OPENAI_API_KEY=... uv run python -m data_product_agent_app_example.chat_terminal --model gpt-4o --autoload-mcp-tools
```

Run in Docker Compose:

```bash
OPENAI_API_KEY=... docker compose --profile chat run --rm agent-chat
```

Docker Compose now runs the API directly and uses a one-shot `registry-hydrator` service to seed products once at startup.
