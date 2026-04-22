from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pprint import pformat

from graph import build_graph

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def load_environment() -> None:
    if load_dotenv is not None:
        load_dotenv(override=True)


def configure_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


async def run(topic: str) -> None:
    async with build_graph() as app:
        config = {"configurable": {"thread_id": f"research::{topic}"}}
        initial_state = {
            "topic": topic,
            "plan": [],
            "queries": [],
            "content": [],
            "analysis": {},
            "analysis_summary": "",
            "review": {},
            "report": "",
            "revision_count": 0,
        }

        print(f"[topic] {topic}")
        print(f"[model_provider] {os.getenv('MODEL_PROVIDER', 'openai')}")
        print("[workflow] starting...\n")

        async for event in app.astream(initial_state, config=config, stream_mode="updates"):
            print("[event]")
            print(pformat(event, sort_dicts=False))
            print()

        final_state = await app.aget_state(config)
        values = final_state.values

        print("[final review]")
        print(pformat(values.get("review", {}), sort_dicts=False))
        print()
        print("[final analysis summary]")
        print(values.get("analysis_summary", ""))
        print()
        print("[final report]")
        print(values.get("report", ""))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automated multi-agent research report generator.")
    parser.add_argument("topic", help="Research topic or company name.")
    return parser.parse_args()


if __name__ == "__main__":
    load_environment()
    configure_output()
    configure_logging()
    args = parse_args()
    asyncio.run(run(args.topic))
