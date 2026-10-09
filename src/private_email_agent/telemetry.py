from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class JsonlTelemetry:
    """Local-only trace. Never records environment variables, OAuth data, or HTTP headers."""

    def __init__(self, path: str | None):
        self.path = Path(path).expanduser() if path else None

    def emit(self, event: str, **fields: Any) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {"ts": time.time(), "event": event, **fields}
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

