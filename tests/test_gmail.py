import base64

from private_email_agent.gmail import normalize_message


def encoded(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_normalizes_headers_and_multipart_plain_body():
    raw = {
        "id": "m1", "threadId": "t1", "internalDate": "1700000000000",
        "labelIds": ["INBOX"], "snippet": "Your order shipped",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [{"name": "Subject", "value": "Order update"}, {"name": "X-Secret", "value": "omit"}],
            "parts": [{"mimeType": "text/plain", "body": {"data": encoded("Delivered today")}}],
        },
    }
    result = normalize_message(raw)
    assert result["body"] == "Delivered today"
    assert result["headers"] == {"subject": "Order update"}
    assert result["thread_id"] == "t1"


def test_decodes_html_fallback():
    raw = {"id": "m2", "payload": {"mimeType": "text/html", "body": {"data": encoded("<b>Placed</b> Jan 2")}}}
    assert normalize_message(raw)["body"] == "Placed Jan 2"

