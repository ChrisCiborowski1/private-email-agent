from __future__ import annotations

import json
import sys
import time
from typing import Any

from .mcp_codec import result_text, retrieval_count, tool_schema
from .prompts import system_prompt
from .query_planning import broad_search_query
from .telemetry import JsonlTelemetry

# Preserve the original public imports while callers migrate to the focused modules.
from .llm import LlamaClient as LlamaClient
from .mcp_client import run_with_stdio as run_with_stdio


class EmailAgent:
    """Coordinate the model and a connected email-retrieval MCP session."""

    def __init__(self, llm: Any, telemetry: JsonlTelemetry, max_steps: int = 8):
        self.llm = llm
        self.telemetry = telemetry
        self.max_steps = max_steps

    async def answer(self, question: str, session: Any) -> str:
        listed = await session.list_tools()
        tools = [tool_schema(tool) for tool in listed.tools]
        allowed = {tool["function"]["name"] for tool in tools}
        prompt = system_prompt()
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": question}]
        self.telemetry.emit("prompt", system=prompt, question=question, tool_count=len(tools))

        await self._bootstrap_search(question, session, messages)

        model_latency_ms = 0.0
        for step in range(1, self.max_steps + 1):
            started = time.perf_counter()
            reply = await self.llm.complete(messages, tools)
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            model_latency_ms = round(model_latency_ms + latency_ms, 1)
            self.telemetry.emit(
                "model_call",
                step=step,
                latency_ms=latency_ms,
                tool_call_count=len(reply.get("tool_calls") or []),
            )
            messages.append(reply)
            calls = reply.get("tool_calls") or []
            if not calls:
                answer = reply.get("content") or "I could not produce an answer."
                self.telemetry.emit(
                    "final_answer",
                    step=step,
                    answer=answer,
                    model_latency_ms=model_latency_ms,
                )
                print(f"model latency: {model_latency_ms} ms", file=sys.stderr)
                return answer
            for call in calls:
                await self._invoke_model_tool(call, step, allowed, session, messages)

        raise RuntimeError(f"Agent exceeded {self.max_steps} model steps")

    async def _bootstrap_search(self, question: str, session: Any, messages: list[dict]) -> None:
        arguments = {"query": broad_search_query(question), "limit": 10}
        content = await self._call_tool(
            session, "search_email", arguments, step=0, bootstrap=True
        )
        messages.extend([
            {"role": "assistant", "content": None, "tool_calls": [{
                "id": "bootstrap-search",
                "type": "function",
                "function": {"name": "search_email", "arguments": json.dumps(arguments)},
            }]},
            {
                "role": "tool",
                "tool_call_id": "bootstrap-search",
                "name": "search_email",
                "content": content,
            },
        ])

    async def _invoke_model_tool(
        self,
        call: dict,
        step: int,
        allowed: set[str],
        session: Any,
        messages: list[dict],
    ) -> None:
        name = call["function"]["name"]
        if name not in allowed:
            raise RuntimeError(f"Model requested unknown tool: {name}")
        try:
            arguments = json.loads(call["function"].get("arguments") or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid arguments for {name}") from exc
        content = await self._call_tool(session, name, arguments, step=step)
        messages.append({
            "role": "tool",
            "tool_call_id": call["id"],
            "name": name,
            "content": content,
        })

    async def _call_tool(
        self,
        session: Any,
        name: str,
        arguments: dict,
        *,
        step: int,
        bootstrap: bool = False,
    ) -> str:
        started = time.perf_counter()
        result = await session.call_tool(name, arguments=arguments)
        content = result_text(result)
        fields = {
            "step": step,
            "tool": name,
            "arguments": arguments,
            "retrieval_count": retrieval_count(content),
            "result_chars": len(content),
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "is_error": bool(getattr(result, "isError", False)),
        }
        if bootstrap:
            fields["bootstrap"] = True
        self.telemetry.emit("tool_call", **fields)
        return content

