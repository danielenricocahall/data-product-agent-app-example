from __future__ import annotations

import os
from datetime import timezone

from http import HTTPStatus
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query

from data_product_agent_app_example.products import DataProduct, PiiClass, Capability

app = FastAPI(title="Data Product Registry", version="0.1.0")



REGISTRY: dict[tuple[str, str, str], DataProduct] = {}


def _key(domain: str, name: str, version: str) -> tuple[str, str, str]:
    return domain.lower(), name.lower(), version


@app.put("/products/{domain}/{name}/{version}", response_model=DataProduct)
def upsert_data_product_to_registry(domain: str, name: str, version: str, product: DataProduct) -> DataProduct:
    if product.domain.lower() != domain.lower():
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Body.domain must match path domain")
    if product.name.lower() != name.lower():
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Body.name must match path name")
    if product.version != version:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Body.version must match path version")

    if product.updated_at.tzinfo is None:
        product.updated_at = product.updated_at.replace(tzinfo=timezone.utc)

    REGISTRY[_key(domain, name, version)] = product
    return product


@app.get("/products", response_model=list[dict[str, Any]])
def list_products(
    domain: Optional[str] = None,
    pii: Optional[PiiClass] = None,
    q: Optional[str] = Query(default=None, description="Search in name/description/owner_team"),
    capability: Optional[str] = Query(default=None, description="Filter products that expose capability"),
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for (d, n, v), prod in REGISTRY.items():
        if domain and d != domain.lower():
            continue
        if pii and prod.governance.pii != pii:
            continue
        if q:
            cap_text = " ".join(
                f"{c.name} {c.description}" for c in prod.capabilities
            )
            haystack = f"{prod.name} {prod.description} {prod.owner_team} {prod.domain} {cap_text}".lower()
            stop_words = {"what", "are", "the", "for", "a", "an", "of", "in", "to", "is", "and", "or", "our", "my", "me"}
            keywords = [w for w in q.lower().split() if w not in stop_words]
            if keywords and not any(kw in haystack for kw in keywords):
                continue
        if capability:
            cap_names = {c.name.lower() for c in prod.capabilities}
            if capability.lower() not in cap_names:
                continue

        # return a light “card” for discovery (agents/humans)
        results.append(
            {
                "domain": prod.domain,
                "name": prod.name,
                "version": prod.version,
                "description": prod.description,
                "owner_team": prod.owner_team,
                "pii": prod.governance.pii,
                "updated_at": prod.updated_at,
                "capabilities": [c.name for c in prod.capabilities],
            }
        )

    # newest first
    results.sort(key=lambda x: x["updated_at"], reverse=True)
    return results


@app.get("/products/{domain}/{name}/{version}", response_model=DataProduct)
def get_product(domain: str, name: str, version: str) -> DataProduct:
    k = _key(domain, name, version)
    if k not in REGISTRY:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Not found")
    return REGISTRY[k]


@app.get("/products/{domain}/{name}/{version}/capabilities/{capability_name}", response_model=Capability)
def get_capability(domain: str, name: str, version: str, capability_name: str) -> Capability:
    prod = get_product(domain, name, version)
    for cap in prod.capabilities:
        if cap.name.lower() == capability_name.lower():
            return cap
    raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Capability not found")


@app.get("/health")
def health() -> dict[str, str | int]:
    return {"status": "ok", "products": len(REGISTRY)}

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
