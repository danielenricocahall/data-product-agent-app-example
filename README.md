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

### Endpoints

- `GET /health`
- `GET /contracts`
- `GET /contracts/{contract_id}`
