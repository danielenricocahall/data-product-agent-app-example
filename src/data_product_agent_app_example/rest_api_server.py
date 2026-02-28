from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import FastAPI, Query
import uvicorn

app = FastAPI(title="Lead Funnel Health REST API", version="1.0.0")

MOCK_CONVERSIONS: list[dict[str, Any]] = [
    {"week_start": "2026-02-10", "stage_from": "MQL", "stage_to": "SQL", "conversion_rate": 0.32, "volume": 148, "avg_days": 4.2},
    {"week_start": "2026-02-10", "stage_from": "SQL", "stage_to": "Opportunity", "conversion_rate": 0.45, "volume": 47, "avg_days": 7.1},
    {"week_start": "2026-02-10", "stage_from": "Opportunity", "stage_to": "Closed-Won", "conversion_rate": 0.28, "volume": 13, "avg_days": 18.5},
    {"week_start": "2026-02-17", "stage_from": "MQL", "stage_to": "SQL", "conversion_rate": 0.29, "volume": 134, "avg_days": 4.8},
    {"week_start": "2026-02-17", "stage_from": "SQL", "stage_to": "Opportunity", "conversion_rate": 0.41, "volume": 39, "avg_days": 6.9},
    {"week_start": "2026-02-17", "stage_from": "Opportunity", "stage_to": "Closed-Won", "conversion_rate": 0.31, "volume": 12, "avg_days": 16.3},
    {"week_start": "2026-02-24", "stage_from": "MQL", "stage_to": "SQL", "conversion_rate": 0.35, "volume": 161, "avg_days": 3.9},
    {"week_start": "2026-02-24", "stage_from": "SQL", "stage_to": "Opportunity", "conversion_rate": 0.48, "volume": 56, "avg_days": 7.4},
    {"week_start": "2026-02-24", "stage_from": "Opportunity", "stage_to": "Closed-Won", "conversion_rate": 0.25, "volume": 14, "avg_days": 19.1},
]


@app.get("/stage-conversion")
def get_stage_conversion(
    week_start: Optional[str] = Query(default=None, description="Filter by week start date (YYYY-MM-DD)"),
) -> dict[str, Any]:
    rows = MOCK_CONVERSIONS
    if week_start:
        rows = [r for r in rows if r["week_start"] == week_start]
    return {"conversion": rows, "row_count": len(rows)}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("REST_API_PORT", "9001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
