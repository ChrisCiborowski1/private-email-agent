from __future__ import annotations

from typing import Any, Protocol


class EmailRetrieval(Protocol):
    """Boundary implemented by Gmail today and encrypted MySudo retrieval later."""

    def search_email(self, query: str, limit: int = 10) -> dict[str, Any]: ...

    def get_message(self, message_id: str) -> dict[str, Any]: ...

    def get_thread(self, thread_id: str) -> dict[str, Any]: ...

