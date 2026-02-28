from __future__ import annotations

import argparse
import asyncio
import os
from typing import Any

from agents import build_agent_for_query


def _stringify_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    return str(content)


async def run_chat_terminal(*, model_name: str = "gpt-4o", autoload_mcp_tools: bool = True, show_metadata: bool = False) -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required")

    print("Data Product Agent Chat")
    print("Commands: /help, /reset, /exit")

    messages: list[tuple[str, str]] = []

    while True:
        try:
            user_input = input("\nyou> ").strip()
        except EOFError:
            print("\nExiting chat.")
            return
        except KeyboardInterrupt:
            print("\nExiting chat.")
            return

        if not user_input:
            continue

        if user_input in {"/exit", "exit", "quit"}:
            print("Exiting chat.")
            return
        if user_input == "/help":
            print("Type a question about data products.")
            print("Use /reset to clear conversation history.")
            print("Use /exit to quit.")
            continue
        if user_input == "/reset":
            messages = []
            print("Conversation history cleared.")
            continue

        messages.append(("human", user_input))

        agent, metadata = await build_agent_for_query(
            user_input,
            model_name=model_name,
            autoload_mcp_tools=autoload_mcp_tools,
        )
        response = await agent.ainvoke({"messages": messages})
        assistant_text = _stringify_content(response["messages"][-1].content)

        print(f"agent> {assistant_text}")
        if show_metadata:
            print(f"metadata> {metadata}")

        messages.append(("assistant", assistant_text))


async def _amain() -> None:
    parser = argparse.ArgumentParser(description="Interactive terminal chat for the data product agent")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model name")
    parser.add_argument(
        "--autoload-mcp-tools",
        action="store_true",
        default=True,
        help="Auto-load MCP tools when product MCP capability is detected",
    )
    parser.add_argument(
        "--no-autoload-mcp-tools",
        dest="autoload_mcp_tools",
        action="store_false",
        help="Disable auto-loading MCP tools",
    )
    parser.add_argument("--show-metadata", action="store_true", help="Print metadata after each response")
    args = parser.parse_args()

    await run_chat_terminal(
        model_name=args.model,
        autoload_mcp_tools=args.autoload_mcp_tools,
        show_metadata=args.show_metadata,
    )


if __name__ == "__main__":
    asyncio.run(_amain())
