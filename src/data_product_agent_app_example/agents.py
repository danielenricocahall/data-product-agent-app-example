from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
from typing import Any
from urllib import error, parse, request
from urllib.parse import urlparse

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI


def _registry_api_url() -> str:
    return os.getenv("REGISTRY_API_URL", "http://registry-api:8000").rstrip("/")


def _http_json(
    method: str,
    url: str,
    *,
    query: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 10,
) -> Any:
    request_url = url
    if query:
        params = {k: v for k, v in query.items() if v is not None and str(v) != ""}
        if params:
            request_url = f"{url}?{parse.urlencode(params)}"

    body: bytes | None = None
    headers: dict[str, str] = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(request_url, method=method, data=body, headers=headers)
    with request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
        if not raw.strip():
            return {}
        return json.loads(raw)


def _list_registry_products_raw(
    *,
    domain: str | None = None,
    pii: str | None = None,
    query: str | None = None,
    capability: str | None = None,
) -> list[dict[str, Any]]:
    return _http_json(
        "GET",
        f"{_registry_api_url()}/products",
        query={"domain": domain, "pii": pii, "q": query, "capability": capability},
    )


def _get_registry_product_raw(domain: str, name: str, version: str) -> dict[str, Any]:
    return _http_json("GET", f"{_registry_api_url()}/products/{domain}/{name}/{version}")


def _normalize_mcp_url(server_url: str) -> str:
    base = server_url.rstrip("/")
    parsed = urlparse(base)
    if parsed.path.endswith("/mcp"):
        return base
    if parsed.path in ("", "/"):
        return f"{base}/mcp"
    return f"{base}/mcp"


def _tool_safe_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().lower()).strip("_")
    return cleaned or "tool"


def _bounded_tool_name(value: str, max_len: int = 64) -> str:
    safe_name = _tool_safe_name(value)
    if len(safe_name) <= max_len:
        return safe_name

    digest = hashlib.sha1(safe_name.encode("utf-8")).hexdigest()[:10]
    suffix = f"_{digest}"
    head = safe_name[: max_len - len(suffix)]
    return f"{head}{suffix}"


def _capability_descriptor(product: dict[str, Any], capability: dict[str, Any]) -> dict[str, Any]:
    invocation = capability.get("invocation", {})
    server_url = invocation.get("server_url")
    return {
        "domain": product.get("domain"),
        "product_name": product.get("name"),
        "version": product.get("version"),
        "capability_name": capability.get("name"),
        "description": capability.get("description"),
        "invocation_type": invocation.get("type"),
        "rest_method": invocation.get("method"),
        "rest_url": invocation.get("url"),
        "server_url": server_url,
        "mcp_endpoint": _normalize_mcp_url(server_url) if server_url else None,
        "tool_name": invocation.get("tool_name"),
        "input_schema": capability.get("input_schema", {}),
        "output_schema": capability.get("output_schema", {}),
        "policy_hints": capability.get("policy_hints", {}),
    }


def _discover_capabilities(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    capabilities: list[dict[str, Any]] = []
    for product in products:
        for capability in product.get("capabilities", []):
            if not isinstance(capability, dict):
                continue
            capabilities.append(_capability_descriptor(product, capability))
    return capabilities


def _best_match_card(user_query: str, cards: list[dict[str, Any]]) -> dict[str, Any] | None:
    q = user_query.lower().strip()
    if not q:
        return None
    for card in cards:
        text = f"{card.get('domain', '')} {card.get('name', '')} {card.get('description', '')}".lower()
        if card.get("name", "").lower() in q or card.get("domain", "").lower() in q or q in text:
            return card
    return None


def _build_rest_capability_tool(cap: dict[str, Any]) -> Any:
    tool_name = _bounded_tool_name(
        f"invoke_{cap['domain']}_{cap['product_name']}_{cap['version']}_{cap['capability_name']}"
    )
    method = str(cap.get("rest_method") or "GET").upper()
    rest_url = str(cap.get("rest_url") or "")
    domain = str(cap.get("domain") or "")
    product_name = str(cap.get("product_name") or "")
    version = str(cap.get("version") or "")
    capability_name = str(cap.get("capability_name") or "")
    description = str(cap.get("description") or "")
    input_schema = cap.get("input_schema", {})

    @tool(tool_name)
    def invoke_capability(arguments_json: str = "{}") -> dict[str, Any]:
        """Invoke a registry capability via REST using JSON-encoded arguments."""
        try:
            args = json.loads(arguments_json or "{}")
        except json.JSONDecodeError as exc:
            return {"error": f"Invalid JSON for arguments_json: {exc}"}

        if not isinstance(args, dict):
            return {"error": "arguments_json must deserialize to a JSON object"}

        base_url = _registry_api_url()
        target_url = rest_url if rest_url.startswith("http://") or rest_url.startswith("https://") else f"{base_url}{rest_url}"

        try:
            if method == "GET":
                response = _http_json("GET", target_url, query=args)
            else:
                response = _http_json(method, target_url, payload=args)
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            return {
                "error": "Capability invocation failed",
                "status": exc.code,
                "details": details,
                "target_url": target_url,
                "method": method,
            }
        except Exception as exc:
            return {"error": f"Capability invocation failed: {exc}", "target_url": target_url, "method": method}

        return {
            "domain": domain,
            "product_name": product_name,
            "version": version,
            "capability_name": capability_name,
            "method": method,
            "target_url": target_url,
            "arguments": args,
            "result": response,
        }

    invoke_capability.__doc__ = (
        f"Invoke REST capability '{capability_name}' for product '{product_name}' "
        f"({domain}/{version}). Description: {description}. "
        f"Input schema: {json.dumps(input_schema)}"
    )
    return invoke_capability


async def _load_mcp_tools(capabilities: list[dict[str, Any]]) -> list[Any]:
    connections: dict[str, dict[str, str]] = {}
    seen: set[str] = set()
    idx = 1

    for cap in capabilities:
        if cap.get("invocation_type") != "mcp":
            continue
        endpoint = cap.get("mcp_endpoint")
        if not endpoint or endpoint in seen:
            continue
        seen.add(str(endpoint))
        connections[f"mcp_server_{idx}"] = {"transport": "streamable_http", "url": str(endpoint)}
        idx += 1

    if not connections:
        return []

    client = MultiServerMCPClient(connections)
    return await client.get_tools()


@tool
def list_registry_products(
    domain: str = "",
    pii: str = "",
    query: str = "",
    capability: str = "",
) -> list[dict[str, Any]]:
    """List products from the registry API. Optional filters: domain, pii, query, capability."""
    return _list_registry_products_raw(domain=domain or None, pii=pii or None, query=query or None, capability=capability or None)


@tool
def find_registry_products(query: str) -> list[dict[str, Any]]:
    """Search registry products by query string against name, description, and owner team."""
    return _list_registry_products_raw(query=query)


@tool
def get_registry_product(domain: str, name: str, version: str) -> dict[str, Any]:
    """Get one full registry product definition by domain/name/version."""
    return _get_registry_product_raw(domain, name, version)


@tool
def discover_registry_capabilities(query: str = "") -> list[dict[str, Any]]:
    """Discover capability invocation metadata from registry products, optionally filtered by query."""
    cards = _list_registry_products_raw(query=query or None)
    products = [_get_registry_product_raw(card["domain"], card["name"], card["version"]) for card in cards]
    return _discover_capabilities(products)


def _base_agent_tools() -> list[Any]:
    return [list_registry_products, find_registry_products, get_registry_product, discover_registry_capabilities]


async def build_agent_for_query(
    user_query: str,
    *,
    model_name: str = "gpt-4o",
    autoload_mcp_tools: bool = False,
) -> tuple[Any, dict[str, Any]]:
    model = ChatOpenAI(model=model_name)
    tools = _base_agent_tools()
    metadata: dict[str, Any] = {
        "registry_api_url": _registry_api_url(),
        "dynamic_mcp_tools_loaded": False,
        "dynamic_rest_tools_loaded": 0,
    }

    discovered_caps: list[dict[str, Any]] = []
    try:
        candidate_cards = _list_registry_products_raw(query=user_query or None)
        if not candidate_cards:
            candidate_cards = _list_registry_products_raw()
        if candidate_cards:
            match = _best_match_card(user_query, candidate_cards)
            metadata["matched_product"] = match
            candidates = [match] if match else candidate_cards[:5]
            full_products = [_get_registry_product_raw(card["domain"], card["name"], card["version"]) for card in candidates if card]
            discovered_caps = _discover_capabilities(full_products)
            metadata["discovered_capabilities"] = discovered_caps
    except Exception as exc:
        metadata["registry_discovery_error"] = str(exc)

    for cap in discovered_caps:
        if cap.get("invocation_type") == "rest":
            tools.append(_build_rest_capability_tool(cap))
            metadata["dynamic_rest_tools_loaded"] = int(metadata["dynamic_rest_tools_loaded"]) + 1

    if autoload_mcp_tools and discovered_caps:
        try:
            tools.extend(await _load_mcp_tools(discovered_caps))
            metadata["dynamic_mcp_tools_loaded"] = True
        except Exception as exc:
            metadata["dynamic_mcp_tools_error"] = str(exc)

    serialized_capabilities = json.dumps(discovered_caps[:20], default=str)
    system_prompt = (
        "You are a data product assistant. The registry is available at "
        f"{_registry_api_url()}. Use the registry tools first to discover products and capabilities, then invoke "
        "runtime tools when needed. If no runtime tool exists yet, call discover tools/get product first. "
        "Include server_url/mcp_endpoint in answers when MCP capabilities are relevant. "
        f"Discovered capabilities for this turn: {serialized_capabilities}"
    )

    agent = create_agent(model, tools, system_prompt=system_prompt)
    metadata["tool_count"] = len(tools)
    return agent, metadata


async def run_query(
    query: str,
    *,
    model_name: str = "gpt-4.1",
    autoload_mcp_tools: bool = False,
) -> dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required")

    agent, metadata = await build_agent_for_query(
        query,
        model_name=model_name,
        autoload_mcp_tools=autoload_mcp_tools,
    )
    response = await agent.ainvoke({"messages": [("human", query)]})
    return {"metadata": metadata, "response": response["messages"][-1].content}


async def _amain() -> None:
    parser = argparse.ArgumentParser(description="Run data-product LangChain agent")
    parser.add_argument("query", help="User query for the agent")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model name")
    parser.add_argument(
        "--autoload-mcp-tools",
        action="store_true",
        default=False,
        help="Auto-load MCP tools discovered from the registry",
    )
    args = parser.parse_args()

    result = await run_query(
        args.query,
        model_name=args.model,
        autoload_mcp_tools=args.autoload_mcp_tools,
    )
    print(result["metadata"])
    print(result["response"])


if __name__ == "__main__":
    asyncio.run(_amain())
