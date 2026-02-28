# Data Product Agent App Example

An example application that pairs a **data product registry** with a **LangChain agent** that can discover registered products and dynamically invoke their capabilities at runtime.

### What's in the box

- **Pydantic data product models** — domain, lineage, governance (PII classification, allowed/prohibited use cases, retention), and typed capabilities (MCP, REST, SQL)
- **FastAPI registry API** — in-memory CRUD registry for data products with search/filter support
- **Mock MCP server** — a [FastMCP](https://github.com/jlowin/fastmcp) server that exposes a sample `campaign_kpis_tool`
- **LangChain agent** — discovers products from the registry, dynamically wires up MCP and REST tools, and answers natural-language queries
- **Interactive chat terminal** — REPL-style CLI for conversing with the agent

Three sample data products are included (ads/campaign-performance, crm/lead-funnel-health, finance/invoice-collection-forecast).

---

## Local Setup

Requires **Python 3.13** and [**uv**](https://docs.astral.sh/uv/).

```bash
# install dependencies
uv sync
```

### 1. Start the registry API

```bash
uv run fastapi dev src/data_product_agent_app_example/app.py
```

### 2. Start the mock MCP server (separate terminal)

```bash
uv run python -m data_product_agent_app_example.mcp_server
```

### 3. Hydrate sample data products into the registry

```bash
REGISTRY_API_URL=http://localhost:8000 MCP_SERVER_URL=http://localhost:9000 \
  uv run python -m data_product_agent_app_example.hydrate_registry
```

### 4. Run the agent

One-shot query:

```bash
OPENAI_API_KEY=... REGISTRY_API_URL=http://localhost:8000 \
  uv run python -m data_product_agent_app_example.agents "campaign-performance"
```

Interactive chat:

```bash
OPENAI_API_KEY=... REGISTRY_API_URL=http://localhost:8000 \
  uv run python -m data_product_agent_app_example.chat_terminal --model gpt-4o --autoload-mcp-tools
```

Add `--autoload-mcp-tools` to dynamically load MCP tools discovered from the registry via `MultiServerMCPClient`.

---

## Docker Compose

Docker Compose runs the registry API, mock MCP server, a one-shot hydrator, and (optionally) the chat agent:

```bash
# start registry + MCP server + hydrate seed data
docker compose up -d

# launch the interactive chat agent
OPENAI_API_KEY=... docker compose --profile chat run --rm agent-chat
```

---

## API Reference

**Registry API** (`:8000`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/products` | List/search products (query params: `domain`, `pii`, `q`, `capability`) |
| `GET` | `/products/{domain}/{name}/{version}` | Get a single product |
| `PUT` | `/products/{domain}/{name}/{version}` | Upsert a product |
| `GET` | `/products/{domain}/{name}/{version}/capabilities/{capability_name}` | Get a single capability |

**Mock MCP Server** (`:9000`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/mcp` | MCP tool endpoint |
