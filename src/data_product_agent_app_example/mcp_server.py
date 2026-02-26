from __future__ import annotations

import os
from typing import Any

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

mcp = FastMCP(name="Mock MCP Server", instructions="Provides mock campaign KPI tools.")


MCP_DATASETS: dict[str, list[dict[str, Any]]] = {
    "campaign_kpis_tool": [
        {"date": "2026-02-20", "channel": "search", "spend": 4200.0, "clicks": 3180, "conversions": 212, "roas": 3.4},
        {"date": "2026-02-21", "channel": "social", "spend": 2800.0, "clicks": 2150, "conversions": 143, "roas": 2.9},
        {"date": "2026-02-22", "channel": "display", "spend": 1500.0, "clicks": 980, "conversions": 64, "roas": 2.1},
    ]
}


@mcp.tool
def campaign_kpis_tool(channel: str | None = None) -> dict[str, Any]:
    """Return campaign KPI rows, optionally filtered by channel."""
    rows = MCP_DATASETS["campaign_kpis_tool"]
    if channel:
        rows = [r for r in rows if r.get("channel", "").lower() == str(channel).lower()]

    return {"tool_name": "campaign_kpis_tool", "arguments": {"channel": channel}, "rows": rows, "row_count": len(rows)}


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_: Request) -> Response:
    return JSONResponse({"status": "ok"})


def main() -> None:
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "9000"))
    path = os.getenv("MCP_PATH", "/mcp")
    mcp.run(transport="http", host=host, port=port, path=path)


if __name__ == "__main__":
    main()
