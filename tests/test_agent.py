import json
from types import SimpleNamespace

from private_email_agent.agent import EmailAgent
from private_email_agent.telemetry import JsonlTelemetry


class FakeLLM:
    def __init__(self):
        self.calls = 0

    async def complete(self, messages, tools):
        self.calls += 1
        if self.calls == 1:
            assert messages[-1]["role"] == "tool"
            return {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call-1", "type": "function",
                "function": {"name": "search_email", "arguments": json.dumps({"query": "Banana Republic order", "limit": 5})},
            }]}
        assert messages[-1]["role"] == "tool"
        return {"role": "assistant", "content": "The order was delivered on Jan 5."}


class FakeSession:
    def __init__(self):
        self.tool_calls = 0

    async def list_tools(self):
        tool = SimpleNamespace(name="search_email", description="search", inputSchema={"type": "object"})
        return SimpleNamespace(tools=[tool])

    async def call_tool(self, name, arguments):
        assert name == "search_email"
        self.tool_calls += 1
        assert arguments["limit"] == (10 if self.tool_calls == 1 else 5)
        return SimpleNamespace(
            structuredContent={"count": 1, "messages": [{"id": "m1", "snippet": "Delivered Jan 5"}]},
            content=[], isError=False,
        )


async def test_agent_calls_tool_and_finishes(tmp_path):
    log = tmp_path / "trace.jsonl"
    answer = await EmailAgent(FakeLLM(), JsonlTelemetry(str(log))).answer("Was it delivered?", FakeSession())
    assert answer == "The order was delivered on Jan 5."
    events = [json.loads(line) for line in log.read_text().splitlines()]
    assert [event["event"] for event in events] == ["prompt", "tool_call", "model_call", "tool_call", "model_call", "final_answer"]
    assert events[1]["bootstrap"] is True
    assert events[3]["retrieval_count"] == 1


def test_broad_search_query_prefers_named_entity():
    from private_email_agent.agent import broad_search_query
    assert broad_search_query("Has my Banana Republic order been delivered, and when was it placed?") == '"Banana Republic"'


async def test_rejects_unknown_tool():
    class BadLLM:
        async def complete(self, messages, tools):
            return {"role": "assistant", "tool_calls": [{"id": "x", "function": {"name": "steal_token", "arguments": "{}"}}]}

    import pytest
    with pytest.raises(RuntimeError, match="unknown tool"):
        await EmailAgent(BadLLM(), JsonlTelemetry(None)).answer("test", FakeSession())
