# Private Email Agent POC

A local, read-only email agent. A llama.cpp model decides which retrieval tools to call; a separate MCP server owns Gmail OAuth and returns only email evidence. OAuth credentials and access tokens are never sent to the model.

```text
question -> agent -> llama-server (localhost)
              |          |
              | tool request
              v
         MCP client -> Gmail MCP server -> Gmail API
                         (OAuth lives here)
```

## What is included

- `search_email_structured(merchant, sender_domain, intent, after, before, gmail_query, limit)`
  for semantic searches without requiring the model to compose Gmail syntax
- `search_email(query, limit)` as an advanced raw Gmail-syntax escape hatch
- `get_message(message_id)` with decoded text content
- `get_thread(thread_id)` with all decoded messages
- an iterative OpenAI-compatible tool-calling loop for `llama-server`
- a deterministic broad-search bootstrap so small models do not have to guess Gmail syntax before seeing evidence
- local JSONL traces for prompts, calls, arguments, retrieval counts, latency, and final answers

## Code layout

The package is split by responsibility:

```text
cli.py              command-line composition only
agent.py            model/tool orchestration loop
llm.py              llama-server HTTP adapter
mcp_client.py       MCP child-process lifecycle
mcp_codec.py        MCP ↔ model wire-format conversion
prompts.py          model policy and current-date prompt
query_planning.py   deterministic bootstrap discovery query
mcp_server.py       MCP tool declarations
search_query.py     structured constraints → Gmail query
retrieval.py        provider-neutral retrieval interface
gmail.py            Gmail OAuth, API access, message decoding
telemetry.py        local JSONL events
```

The dependencies point inward: the CLI composes the pieces, the agent coordinates abstract clients,
and Gmail-specific behavior stays below the retrieval/MCP boundary.

The POC is retrieval-only. It cannot send, modify, or delete mail.

## 1. Install llama.cpp and start a model

On Apple Silicon, install the current llama.cpp build:

```bash
brew install llama.cpp
```

Recommended baseline: **Qwen2.5-7B-Instruct Q4_K_M**. It is small enough for a 16 GB Apple Silicon Mac (roughly 4.7 GB of model weights), has native tool-call handling in llama.cpp, and is materially more reliable for multi-step retrieval than most 1–3B models. Start it directly from Hugging Face:

```bash
llama-server \
  -hf bartowski/Qwen2.5-7B-Instruct-GGUF:Q4_K_M \
  --alias local-email-agent \
  --host 127.0.0.1 --port 8080 \
  --ctx-size 16384 --jinja -fa auto
```

For an 8 GB Mac, try `bartowski/Qwen2.5-3B-Instruct-GGUF` with its `Q4_K_M` file and expect weaker tool selection. For a Mac with 24+ GB, an 8–14B instruct model can improve evidence synthesis. Keep the server on loopback; do not use `--host 0.0.0.0` for this POC.

Verify it:

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/props
```

The `/props` response should expose a tool-aware chat template. llama.cpp documents `--jinja` as the switch for OpenAI-style function calling.

## 2. Create Gmail OAuth credentials

1. In Google Cloud Console, create or select a project.
2. Enable the Gmail API.
3. Configure the OAuth consent screen. If the app is in testing, add your Google account as a test user.
4. Create an OAuth client with application type **Desktop app**.
5. Download its JSON and save it as `credentials.json` in this directory.

Only the `gmail.readonly` scope is requested. On first use a browser window opens for consent and `token.json` is created locally with user-only permissions where the OS allows it. Both files are gitignored.

## 3. Install and run

```bash
cd private-email-agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
```

`.env` is a reference, not automatically loaded. Either keep the defaults or export changed values in your shell. Then ask a question:

```bash
private-email-agent "Has my Banana Republic order been delivered, and when was it placed?"
```

The command starts the Gmail MCP server over stdio, completes OAuth if necessary, calls the local model, and lets it search and inspect messages until it can answer. It stops after eight model turns by default.

For example, a request for late-September Banana Republic orders can call the structured tool with
`merchant="Banana Republic"`, `intent="purchase"`, `after="2026-09-20"`, and
`before="2026-10-01"`. The MCP server translates that into Gmail syntax. Advanced searches may still
use `from:bananarepublic.com`, a discovered order number, or another exact value. Search initially returns
metadata and snippets; full bodies arrive only through `get_message` or `get_thread`.

## Tracing and privacy

By default, traces are written to `logs/agent.jsonl`. They include the question/system prompt, tool arguments, counts, timings, result sizes, and final answer. They intentionally exclude environment variables, OAuth tokens, credential files, and HTTP authorization headers. Tool results themselves are not copied into the trace, but questions, Gmail search terms, and final answers can still be sensitive.

Disable traces for a run:

```bash
private-email-agent --no-log "What was my latest order?"
```

Delete `token.json` to revoke this local session artifact; also revoke the app under your Google Account's third-party access page if needed. Treat `credentials.json`, `token.json`, and trace files as secrets. The model does receive email text returned by tools, because it needs that evidence to answer, but it never receives OAuth material.

## Tests

The tests do not contact Gmail or a model:

```bash
pytest
```

## Current POC limits

- HTML-to-text conversion is intentionally basic; attachments are ignored.
- Search fetches one metadata request per result and does not paginate beyond the requested limit.
- The first OAuth browser flow requires an interactive desktop session.
- Email is untrusted input. The system prompt says not to follow instructions in mail, but a small local model is not a strong security boundary. The server exposes read-only tools to limit impact.

## Primary references

- [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [llama.cpp function calling](https://github.com/ggml-org/llama.cpp/blob/master/docs/function-calling.md)
- [Google Gmail Python quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python)
- [Gmail thread retrieval](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.threads/get)
- [Model Context Protocol Python SDK](https://github.com/modelcontextprotocol/python-sdk)
