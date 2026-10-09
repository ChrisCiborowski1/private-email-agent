from __future__ import annotations

import base64
import html
import os
import re
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
USEFUL_HEADERS = {"from", "to", "cc", "date", "subject", "message-id"}


def _decode(data: str | None) -> str:
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")
    except (ValueError, UnicodeError):
        return ""


def _plain_text(payload: dict[str, Any]) -> str:
    mime = payload.get("mimeType", "")
    body = _decode(payload.get("body", {}).get("data"))
    if mime == "text/plain" and body:
        return body
    parts = payload.get("parts", [])
    plain = [text for part in parts if (text := _plain_text(part))]
    if plain:
        return "\n".join(plain)
    if mime == "text/html" and body:
        no_tags = re.sub(r"<[^>]+>", " ", body)
        return re.sub(r"\s+", " ", html.unescape(no_tags)).strip()
    return ""


def normalize_message(message: dict[str, Any]) -> dict[str, Any]:
    payload = message.get("payload", {})
    headers = {
        item["name"].lower(): item.get("value", "")
        for item in payload.get("headers", [])
        if item.get("name", "").lower() in USEFUL_HEADERS
    }
    return {
        "id": message.get("id"),
        "thread_id": message.get("threadId"),
        "internal_date_ms": message.get("internalDate"),
        "label_ids": message.get("labelIds", []),
        "headers": headers,
        "snippet": message.get("snippet", ""),
        "body": _plain_text(payload),
    }


class GmailRetrieval:
    def __init__(self, service: Any):
        self.service = service

    @classmethod
    def from_oauth(cls, credentials_path: str, token_path: str) -> "GmailRetrieval":
        creds = None
        token = Path(token_path)
        if token.exists():
            creds = Credentials.from_authorized_user_file(token, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            token.parent.mkdir(parents=True, exist_ok=True)
            token.write_text(creds.to_json(), encoding="utf-8")
            try:
                os.chmod(token, 0o600)
            except OSError:
                pass
        return cls(build("gmail", "v1", credentials=creds, cache_discovery=False))

    def search_email(self, query: str, limit: int = 10) -> dict[str, Any]:
        limit = max(1, min(limit, 50))
        response = self.service.users().messages().list(
            userId="me", q=query, maxResults=limit
        ).execute()
        refs = response.get("messages", [])
        results = []
        for ref in refs:
            msg = self.service.users().messages().get(
                userId="me", id=ref["id"], format="metadata",
                metadataHeaders=["From", "Date", "Subject"],
            ).execute()
            results.append(normalize_message(msg))
        return {"query": query, "count": len(results), "messages": results}

    def get_message(self, message_id: str) -> dict[str, Any]:
        msg = self.service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        return normalize_message(msg)

    def get_thread(self, thread_id: str) -> dict[str, Any]:
        thread = self.service.users().threads().get(
            userId="me", id=thread_id, format="full"
        ).execute()
        messages = [normalize_message(m) for m in thread.get("messages", [])]
        return {"id": thread.get("id"), "count": len(messages), "messages": messages}
