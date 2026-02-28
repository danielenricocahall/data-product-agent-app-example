# Data Product Agent App Example

An example application that pairs a **data product registry** with a **LangChain agent** that can discover registered products and dynamically invoke their capabilities at runtime.

### What's in the box

- **Pydantic data product models** — domain, lineage, governance (PII classification, allowed/prohibited use cases, retention), and typed capabilities (MCP, REST, SQL)
- **FastAPI registry API** — in-memory CRUD registry for data products with search/filter support
- **Mock MCP server** — a [FastMCP](https://github.com/jlowin/fastmcp) server that exposes a sample `campaign_kpis_tool` (ads/campaign-performance)
- **Mock REST API server** — a FastAPI server that serves stage-conversion data (crm/lead-funnel-health)
- **LangChain agent** — discovers products from the registry, dynamically wires up MCP and REST tools, and answers natural-language queries
- **Interactive chat terminal** — REPL-style CLI for conversing with the agent

Three sample data products are included (ads/campaign-performance, crm/lead-funnel-health, finance/invoice-collection-forecast).

### How it works

The registry acts as a **catalog/contract layer** — it doesn't hold data itself, but declares *where* and *how* to get it. The agent uses the registry to wire up the right tools on the fly for each query.

1. **Registry hydration** — On startup, seed data products are loaded into the registry API. Each product declares its domain, governance rules, and **capabilities** — typed invocation descriptors that point to an MCP server or REST endpoint.
2. **Per-query discovery** — When a user sends a question, the agent searches the registry for relevant products, extracts their capability metadata, and dynamically builds LangChain tools:
   - **REST** capabilities become tools that know the method, URL, and schema
   - **MCP** capabilities are loaded by connecting to the declared server URL via `MultiServerMCPClient` and pulling its tool definitions
3. **Execution** — The LLM calls the dynamically wired tools to fetch real data and answers the user's question, with full awareness of governance constraints and lineage from the registry.

```
┌──────────┐  search   ┌──────────┐  capability   ┌───────────┐
│   User   │──────────▶│ Registry │──────────────▶│ MCP / REST│
│  Query   │           │   API    │  descriptors   │  Servers  │
└──────────┘           └──────────┘               └───────────┘
      │                      │                          │
      ▼                      ▼                          ▼
┌─────────────────────────────────────────────────────────────┐
│  LangChain Agent                                            │
│  - static tools: search/browse registry                     │
│  - dynamic tools: invoke MCP & REST capabilities            │
└─────────────────────────────────────────────────────────────┘
```

### Example questions

Once the chat agent is running, try these to see the different invocation paths:

- **"What are the campaign KPIs for search?"** — The agent discovers the `ads/campaign-performance` product, connects to the MCP server, and calls the `campaign_kpis_tool` to return KPI data for the search channel.
- **"What are our stage conversions in the lead funnel?"** — The agent finds the `crm/lead-funnel-health` product and its REST capability, but the endpoint requires a `week_start` parameter. The agent asks the user for clarification, and once a week is provided, it calls the REST API and returns the conversion data. This illustrates multi-turn tool use.
- **"What data products do we have?"** — The agent queries the registry and returns all registered products with their domains, descriptions, and capabilities.

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

### 3. Start the mock REST API server (separate terminal)

```bash
uv run python -m data_product_agent_app_example.rest_api_server
```

### 4. Hydrate sample data products into the registry

```bash
uv run python -m data_product_agent_app_example.hydrate_registry
```

### 5. Run the agent

One-shot query:

```bash
OPENAI_API_KEY=... uv run python -m data_product_agent_app_example.agents "campaign-performance"
```

Interactive chat:

```bash
OPENAI_API_KEY=... uv run python -m data_product_agent_app_example.chat_terminal --model gpt-4o --autoload-mcp-tools
```

Add `--autoload-mcp-tools` to dynamically load MCP tools discovered from the registry via `MultiServerMCPClient`.

---

## Docker Compose

Docker Compose runs the registry API, mock MCP server, mock REST API server, a one-shot hydrator, and (optionally) the chat agent:

```bash
# start registry + MCP server + REST API server + hydrate seed data
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

**Lead Funnel REST API** (`:9001`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/stage-conversion` | Stage-to-stage conversion rates (query param: `week_start`) |
