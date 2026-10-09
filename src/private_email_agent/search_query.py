from __future__ import annotations

import re
from datetime import date
from typing import Literal

EmailIntent = Literal["any", "purchase", "promotion", "reservation", "updates"]

INTENT_QUERIES: dict[str, str] = {
    "any": "",
    "purchase": "category:purchases",
    "promotion": "category:promotions",
    "reservation": "category:reservations",
    "updates": "category:updates",
}

DOMAIN_PATTERN = re.compile(
    r"(?=.{1,253}\Z)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,63}\Z"
)


def _gmail_date(value: str, field: str) -> tuple[date, str]:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date in YYYY-MM-DD format") from exc
    return parsed, parsed.strftime("%Y/%m/%d")


def _quoted_phrase(value: str) -> str:
    normalized = " ".join(value.replace('"', " ").replace("\\", " ").split())
    if not normalized:
        raise ValueError("merchant must contain searchable text")
    return f'"{normalized}"'


def build_gmail_query(
    *,
    merchant: str | None = None,
    sender_domain: str | None = None,
    intent: EmailIntent = "any",
    after: str | None = None,
    before: str | None = None,
    gmail_query: str | None = None,
) -> str:
    """Translate semantic email constraints into a Gmail API query."""
    parts: list[str] = []
    after_date: date | None = None
    before_date: date | None = None

    if merchant:
        parts.append(_quoted_phrase(merchant))

    if sender_domain:
        domain = sender_domain.strip().lower().rstrip(".")
        if not DOMAIN_PATTERN.fullmatch(domain):
            raise ValueError("sender_domain must be a domain such as example.com")
        parts.append(f"from:{domain}")

    try:
        intent_query = INTENT_QUERIES[intent]
    except KeyError as exc:
        choices = ", ".join(INTENT_QUERIES)
        raise ValueError(f"intent must be one of: {choices}") from exc
    if intent_query:
        parts.append(intent_query)

    if after:
        after_date, formatted = _gmail_date(after, "after")
        parts.append(f"after:{formatted}")
    if before:
        before_date, formatted = _gmail_date(before, "before")
        parts.append(f"before:{formatted}")
    if after_date and before_date and before_date <= after_date:
        raise ValueError("before must be later than after")

    if gmail_query and gmail_query.strip():
        parts.append(gmail_query.strip())

    if not parts:
        raise ValueError("provide at least one structured constraint or gmail_query")
    return " ".join(parts)
