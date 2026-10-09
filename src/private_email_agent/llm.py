from __future__ import annotations

from typing import Any

import httpx


class LlamaClient:
    """Adapter around llama-server's OpenAI-compatible chat endpoint."""

    def __init__(self, base_url: str, model: str, timeout: float = 120):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.timeout = timeout

    async def complete(self, messages: list[dict], tools: list[dict]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0.0,
            "seed": 42,
            "parallel_tool_calls": False,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.url, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]

