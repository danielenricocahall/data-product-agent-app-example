from __future__ import annotations

import os

from data_product_agent_app_example.registry_seed import hydrate_registry_api


def main() -> None:
    registry_api_url = os.getenv("REGISTRY_API_URL", "http://registry-api:8000")
    hydrated = hydrate_registry_api(registry_api_url)
    print(f"Hydrated {hydrated} products into {registry_api_url}")


if __name__ == "__main__":
    main()
