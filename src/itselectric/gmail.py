"""Gmail API helpers: fetch messages, decode bodies, send emails."""

import base64
import os
import re
from datetime import datetime, timezone
from email.message import Message
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore


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



def load_template(template_name: str, template_dir: str) -> tuple[str, str]:
    """
    Load an email template by name from template_dir.

    File format:
        Subject line
        <blank line>
        Body text (may span multiple lines).
        Supports {name} and {address} substitution via str.format_map().

    Tries .html first, then .txt. Raises FileNotFoundError if neither exists.
    Returns (subject, body).
    """
    for ext in (".html", ".txt"):
        path = os.path.join(template_dir, f"{template_name}{ext}")
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
            parts = content.split("\n\n", 1)
            subject = parts[0].strip()
            body = parts[1].strip() if len(parts) > 1 else ""
            return subject, body
    raise FileNotFoundError(f"Template '{template_name}' not found in {template_dir}")


def send_email(
    creds: Credentials,
    to_email: str,
    subject: str,
    body: str,
    images: dict[str, str] | None = None,
) -> bool:
    """
    Send an HTML email via the authenticated Gmail account.

    If images is provided, sends multipart/related with inline images embedded by CID.
    Reference images in HTML with <img src="cid:KEY"> where KEY matches images dict keys.

    Returns True on success, False on error.
    """
    message: Message
    if images:
        message = MIMEMultipart("related")
        message["to"] = to_email
        message["subject"] = subject
        message.attach(MIMEText(body, "html"))
        for cid, filepath in images.items():
            with open(filepath, "rb") as f:
                img = MIMEImage(f.read())
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline", filename=os.path.basename(filepath))
            message.attach(img)
    else:
        message = MIMEText(body, "html")
        message["to"] = to_email
        message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    service = build("gmail", "v1", credentials=creds)
    try:
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except HttpError as e:
        print(f"Gmail send error: {e}")
        return False
