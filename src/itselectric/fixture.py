"""File-based email source for local dev and integration testing.

Reads .txt files from a directory and returns them as Gmail-compatible
message dicts, so the rest of the pipeline works without modification.
"""

import base64
from pathlib import Path


def load_fixture_messages(directory) -> list[dict]:
    """
    Load all .txt files from a directory as fake Gmail message dicts.

    Files are processed in sorted name order. Each file's plain-text content
    is base64url-encoded into a text/plain payload, exactly as Gmail returns it.
    The message's internalDate is derived from the file's modification time.

    Raises FileNotFoundError if the directory does not exist.
    """
    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(f"Fixture directory not found: {path}")

    messages = []
    for txt_file in sorted(path.glob("*.txt")):
        content = txt_file.read_text(encoding="utf-8")
        encoded = base64.urlsafe_b64encode(content.encode()).decode()
        mtime_ms = int(txt_file.stat().st_mtime * 1000)
        messages.append({
            "internalDate": str(mtime_ms),
            "payload": {
                "mimeType": "text/plain",
                "body": {"data": encoded},
                "headers": [],
            },
        })
    return messages
