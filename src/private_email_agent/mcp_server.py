from __future__ import annotations

import os
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
    """Run an advanced raw Gmail query. Prefer search_email_structured for ordinary requests."""
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
    """Search email without requiring the caller to know Gmail syntax.

    Preserve every user constraint. Use merchant for an organization name,
    intent="purchase" for orders/receipts/shipping, and ISO dates (YYYY-MM-DD).
    `before` is exclusive; for late September 2026 use after="2026-09-20" and
    before="2026-10-01". Never invent sender_domain. gmail_query is an optional
    advanced refinement. Results contain metadata/snippets, not credentials.
    """
    query = build_gmail_query(
        merchant=merchant,
        sender_domain=sender_domain,
        intent=intent,
        after=after,
        before=before,
        gmail_query=gmail_query,
    )
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
    """Retrieve one email, including decoded text body, by Gmail message ID."""
    return backend().get_message(message_id)


@mcp.tool()
def get_thread(thread_id: str) -> dict:
    """Retrieve all messages in an email thread by Gmail thread ID."""
    return backend().get_thread(thread_id)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
