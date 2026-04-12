"""Gmail API helpers: fetch messages, decode bodies."""

import base64
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build  # type: ignore


def decode_base64(data: str) -> str:
    return base64.urlsafe_b64decode(data).decode("utf-8")


def extract_header(payload: dict, field_name: str, default=None):
    headers = payload.get("headers", [])
    return next((h["value"] for h in headers if h["name"] == field_name), default)


def get_body_from_payload(payload: dict) -> tuple[str | None, str | None]:
    """
    Return (mime_type, decoded_text) from a Gmail message payload.
    Handles single-part, multipart, and nested multipart. Prefers text/html.
    Returns (None, None) if no body found.
    """
    parts = payload.get("parts") or []
    if not parts:
        body = payload.get("body") or {}
        data = body.get("data")
        if data:
            return payload.get("mimeType", "text/plain"), decode_base64(data)
        return None, None

    candidates: list[tuple[str, str]] = []

    def collect(part: dict) -> None:
        data = (part.get("body") or {}).get("data")
        if data:
            candidates.append((part.get("mimeType", "text/plain"), decode_base64(data)))
        for sub in part.get("parts") or []:
            collect(sub)

    for part in parts:
        collect(part)

    if not candidates:
        return None, None
    for preferred in ("text/html", "text/plain"):
        for mime, text in candidates:
            if mime == preferred:
                return mime, text
    return candidates[0]


def html_to_plain(html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def body_to_plain(mime_type: str | None, body: str) -> str:
    if mime_type and mime_type.lower() == "text/html":
        return html_to_plain(body)
    return body


def format_sent_date(msg: dict) -> str:
    """Return a human-readable sent date from a Gmail message dict."""
    internal = msg.get("internalDate")
    if internal:
        try:
            ts = int(internal) / 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        except (ValueError, TypeError):
            pass
    date_header = extract_header(msg.get("payload", {}), "Date")
    return date_header or ""


def fetch_messages(creds: Credentials, label: str, max_messages: int) -> list[dict]:
    """
    Fetch up to max_messages Gmail messages from the given label.
    Returns a list of full message dicts (with payload).
    """
    service = build("gmail", "v1", credentials=creds)

    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    label_id = next((lb["id"] for lb in labels if lb["name"] == label), None)
    if not label_id:
        print(f"Label '{label}' not found.")
        return []
    print(f"Label '{label}' ID: {label_id}")

    result = (
        service.users()
        .messages()
        .list(userId="me", labelIds=[label_id], maxResults=max_messages)
        .execute()
    )
    message_ids = [m["id"] for m in result.get("messages", [])]
    print("Message IDs:", message_ids)

    return [
        service.users().messages().get(userId="me", id=msg_id).execute() for msg_id in message_ids
    ]
