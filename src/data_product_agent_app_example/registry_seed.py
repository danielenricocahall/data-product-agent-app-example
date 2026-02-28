from __future__ import annotations

import os
from datetime import datetime, timezone
from urllib import request

from data_product_agent_app_example.app import REGISTRY, _key
from data_product_agent_app_example.products import Capability, DataProduct, Invocation, Lineage, PiiClass, Governance


def example_products() -> list[DataProduct]:
    now = datetime.now(timezone.utc)
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://mcp-server:9000")

    return [
        DataProduct(
            domain="ads",
            name="campaign-performance",
            client="Northwind",
            version="1.0.0",
            owner_team="media-analytics",
            description="Cross-channel campaign performance metrics by day and audience segment.",
            lineage=Lineage(
                source_systems=["google-ads", "meta-ads", "internal-budgeting"],
                transformation_summary="Daily ETL aggregates spend, impressions, clicks, conversions, and ROAS.",
                downstream_consumers=["bid-optimizer", "weekly-business-review", "exec-dashboard"],
            ),
            governance=Governance(
                allowed_use_cases=["campaign optimization", "budget pacing", "performance reporting"],
                prohibited_use_cases=["individual targeting", "credit scoring"],
                retention_days=365,
                pii=PiiClass.NONE,
            ),
            capabilities=[
                Capability(
                    name="get_campaign_kpis",
                    description="Returns KPI series for a date range and channel.",
                    invocation=Invocation(
                        type="mcp",
                        server_url=mcp_server_url,
                        tool_name="campaign_kpis_tool",
                    ),
                    input_schema={"type": "object", "properties": {"start_date": {"type": "string"}, "end_date": {"type": "string"}, "channel": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"rows": {"type": "array"}}},
                    policy_hints={"max_rows": 10000},
                )
            ],
            updated_at=now,
        ),
        DataProduct(
            domain="crm",
            name="lead-funnel-health",
            client="Contoso",
            version="1.2.0",
            owner_team="revops-insights",
            description="Lead funnel conversion and velocity metrics from MQL to closed-won.",
            lineage=Lineage(
                source_systems=["salesforce", "hubspot", "marketing-automation"],
                transformation_summary="Normalizes stage transitions and computes conversion/latency metrics.",
                downstream_consumers=["forecast-model", "sales-ops-dashboard"],
            ),
            governance=Governance(
                allowed_use_cases=["pipeline analytics", "capacity planning"],
                prohibited_use_cases=["employee surveillance", "external resale"],
                retention_days=180,
                pii=PiiClass.PRIVATE,
            ),
            capabilities=[
                Capability(
                    name="get_stage_conversion",
                    description="Returns stage-to-stage conversion rates by week.",
                    invocation=Invocation(
                        type="rest",
                        method="GET",
                        url="/products/crm/lead-funnel-health/1.2.0/capabilities/get_stage_conversion",
                    ),
                    input_schema={"type": "object", "properties": {"week_start": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"conversion": {"type": "array"}}},
                    policy_hints={"requires_role": "revops_analyst"},
                )
            ],
            updated_at=now,
        ),
        DataProduct(
            domain="finance",
            name="invoice-collection-forecast",
            client="Fabrikam",
            version="0.9.1",
            owner_team="finance-data-products",
            description="Forecasted invoice collections with risk buckets and regional rollups.",
            lineage=Lineage(
                source_systems=["netsuite", "collections-crm", "erp"],
                transformation_summary="Joins outstanding invoices and payment history to generate forecast curves.",
                downstream_consumers=["cashflow-planner", "cfo-reporting"],
            ),
            governance=Governance(
                allowed_use_cases=["cashflow forecasting", "collections prioritization"],
                prohibited_use_cases=["consumer credit decisions", "public disclosure"],
                retention_days=90,
                pii=PiiClass.SENSITIVE,

            ),
            capabilities=[
                Capability(
                    name="get_collection_forecast",
                    description="Returns collections forecast by week and risk segment.",
                    invocation=Invocation(
                        type="rest",
                        method="GET",
                        url="/products/finance/invoice-collection-forecast/0.9.1/capabilities/get_collection_forecast",
                    ),
                    input_schema={"type": "object", "properties": {"horizon_weeks": {"type": "integer"}}},
                    output_schema={"type": "object", "properties": {"forecast": {"type": "array"}}},
                    policy_hints={"mask_client_names": True},
                )
            ],
            updated_at=now,
        ),
    ]


def hydrate_in_memory_registry() -> None:
    if REGISTRY:
        return

    for product in example_products():
        REGISTRY[_key(product.domain, product.name, product.version)] = product


def hydrate_registry_api(registry_api_url: str) -> int:
    base_url = registry_api_url.rstrip("/")
    hydrated = 0

    for product in example_products():
        path = f"/products/{product.domain}/{product.name}/{product.version}"
        req = request.Request(
            f"{base_url}{path}",
            method="PUT",
            data=product.model_dump_json().encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with request.urlopen(req, timeout=10):
            hydrated += 1

    return hydrated
