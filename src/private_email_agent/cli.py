from __future__ import annotations

import argparse
import asyncio
import os

from .agent import EmailAgent
from .llm import LlamaClient
from .mcp_client import run_with_stdio
from .telemetry import JsonlTelemetry


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a local LLM questions about Gmail")
    parser.add_argument("question", nargs="+", help="Question to answer from email")
    parser.add_argument("--no-log", action="store_true", help="Disable local JSONL trace")
    args = parser.parse_args()
    llm = LlamaClient(
        os.getenv("LLAMA_BASE_URL", "http://127.0.0.1:8080/v1"),
        os.getenv("LLAMA_MODEL", "local-email-agent"),
    )
    log_path = None if args.no_log else os.getenv("AGENT_LOG_PATH", "logs/agent.jsonl")
    agent = EmailAgent(llm, JsonlTelemetry(log_path), int(os.getenv("AGENT_MAX_STEPS", "8")))
    print(asyncio.run(run_with_stdio(agent, " ".join(args.question))))


if __name__ == "__main__":
    main()
