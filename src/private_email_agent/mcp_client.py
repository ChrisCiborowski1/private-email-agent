from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_with_stdio(agent: Any, question: str, command: str = "private-email-mcp") -> str:
    """Run one question against an MCP server managed as a stdio child process."""
    params = StdioServerParameters(command=command)
    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        return await agent.answer(question, session)

