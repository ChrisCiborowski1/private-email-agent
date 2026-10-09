from __future__ import annotations

import json
from typing import Any


def tool_schema(tool: Any) -> dict[str, Any]:
    """Translate an MCP tool declaration into an OpenAI-compatible declaration."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema,
        },
    }


def result_text(result: Any) -> str:
    """Turn structured or text MCP content into one model-facing string."""
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False)
    return "\n".join(
        item.text
        for item in getattr(result, "content", [])
        if getattr(item, "text", None) is not None
    )


def retrieval_count(content: str) -> int | None:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    return parsed.get("count") if isinstance(parsed, dict) else None

