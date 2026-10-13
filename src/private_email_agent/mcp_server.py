from __future__ import annotations

import os
import sys
from functools import lru_cache

from mcp.server.fastmcp import FastMCP

from .gmail import GmailRetrieval
from .retrieval import EmailRetrieval
from .search_query import EmailIntent, build_gmail_query

mcp = FastMCP("private-email-retrieval")


@lru_cache(maxsize=1)
def backend() -> EmailRetrieval:
    return GmailRetrieval.from_oauth(
        os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json"),
        os.getenv("GMAIL_TOKEN_PATH", "token.json"),
    )


@mcp.tool()
def search_email(query: str, limit: int = 10) -> dict:
    """Advanced raw Gmail search for queries that already contain Gmail operators.

    Do NOT use this for ordinary questions about a merchant, order, receipt, shipment,
    delivery, reservation, or date range. Use search_email_structured for those.
    """
    return backend().search_email(query, limit)


@mcp.tool()
def search_email_structured(
    merchant: str | None = None,
    sender_domain: str | None = None,
    intent: EmailIntent = "any",
    after: str | None = None,
    before: str | None = None,
    gmail_query: str | None = None,
    limit: int = 10,
) -> dict:
    """REQUIRED search for ordinary email questions with semantic constraints.

    Call this tool before answering whenever the user mentions a merchant, order,
    receipt, shipment, delivery, reservation, or date range. A previous broad search
    may contain only promotions; that is NOT evidence that the requested email is
    missing. Filter again here instead of answering or asking the user to search.

    Copy every constraint from the question into the arguments:
    - merchant: the organization or store name supplied by the user
    - intent="purchase": orders, confirmations, receipts, shipping, or delivery
    - after: first included date in YYYY-MM-DD format
    - before: first excluded date in YYYY-MM-DD format
    - sender_domain: only when a domain was found in email evidence; never guess it
    - gmail_query: optional extra Gmail syntax only when the structured fields are
      insufficient

    For a month named without a year, use the runtime current date to select the year.
    Never copy a year from an example. After searching, inspect promising results
    with get_message or get_thread. Results are metadata/snippets, not full message
    bodies.
    """
    query = build_gmail_query(
        merchant=merchant,
        sender_domain=sender_domain,
        intent=intent,
        after=after,
        before=before,
        gmail_query=gmail_query,
    )
    print(f"search_email_structured query: {query}", file=sys.stderr)
    result = backend().search_email(query, limit)
    result["structured_constraints"] = {
        "merchant": merchant,
        "sender_domain": sender_domain,
        "intent": intent,
        "after": after,
        "before": before,
        "gmail_query": gmail_query,
    }
    return result


@mcp.tool()
def get_message(message_id: str) -> dict:
    """Read one promising search result in full by message ID.

    Use this after search to verify facts such as order date, shipping state, or
    delivery state. Do not treat a search-result snippet as complete evidence when
    the full message could answer the question.
    """
    return backend().get_message(message_id)


@mcp.tool()
def get_thread(thread_id: str) -> dict:
    """Read every message in a promising Gmail thread by thread ID.

    Use this when status may have changed across a conversation or order-update
    thread. Prefer the newest explicit status; shipping does not prove delivery.
    """
    return backend().get_thread(thread_id)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
