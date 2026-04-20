"""Google Docs integration: fetch email templates from a Google Doc."""

from bs4 import BeautifulSoup
from googleapiclient.discovery import build  # type: ignore


def fetch_template_from_doc(creds, doc_id: str, template_name: str) -> tuple[str, str]:
    """
    Fetch a named email template from a Google Doc.

    Doc format: H1 headings mark template sections by name. Under each heading:
      first non-empty paragraph = subject line, remaining content = HTML email body.

    Supports {name}, {address}, {city}, {state} substitution in body (done by caller).
    Returns (subject, body_html).
    Raises KeyError if template_name not found in doc.
    Raises ValueError if the section has no content.
    """
    service = build("drive", "v3", credentials=creds)
    content = service.files().export(fileId=doc_id, mimeType="text/html").execute()
    html = content.decode("utf-8")

    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    if not body:
        raise ValueError(f"Google Doc {doc_id!r} has no body content")

    sections: dict[str, list] = {}
    current_name: str | None = None
    current_elems: list = []

    for elem in body.children:
        if not hasattr(elem, "name") or not elem.name:
            continue
        if elem.name == "h1":
            if current_name is not None:
                sections[current_name] = current_elems
            current_name = elem.get_text(strip=True)
            current_elems = []
        elif current_name is not None:
            current_elems.append(elem)

    if current_name is not None:
        sections[current_name] = current_elems

    if template_name not in sections:
        raise KeyError(f"Template '{template_name}' not found in Google Doc {doc_id!r}")

    elements = sections[template_name]

    subject = ""
    body_parts: list[str] = []
    found_subject = False
    for elem in elements:
        text = elem.get_text(strip=True)
        if not found_subject:
            if text:
                subject = text
                found_subject = True
        else:
            body_parts.append(str(elem))

    if not found_subject:
        raise ValueError(
            f"Template '{template_name}' in Google Doc {doc_id!r} has no content"
        )

    return subject, "\n".join(body_parts)
