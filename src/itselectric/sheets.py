"""Google Sheets helpers: read existing rows and append new ones with deduplication."""

import hashlib

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

COLUMNS = [
    "Sent Date",
    "Name",
    "Address",
    "Email 1",
    "Email 2",
    "Content",
    "Nearest Charger",
    "Distance (mi)",
    "HubSpot Contact",   # "created" | "failed" | "" (not attempted)
    "Email Sent",    # template name if sent, "failed", or "" (not attempted)
]


def truncate(s, limit: int) -> str:
    """Normalize and truncate a value to fit within a sheet cell."""
    s = str(s).strip() if s is not None else ""
    return s if len(s) <= limit else s[: limit - 3] + "..."


def _parsed_hash(sent_date: str, name: str, address: str, email_1: str, email_2: str) -> str:
    key = "\n".join(str(x).strip() for x in (sent_date, name, address, email_1, email_2))
    return hashlib.sha256(key.encode()).hexdigest()


def _unparsed_hash(sent_date: str, content: str, content_limit: int) -> str:
    key = str(sent_date).strip() + "\n" + truncate(content, content_limit)
    return hashlib.sha256(key.encode()).hexdigest()


def row_hash(row: list, content_limit: int) -> str:
    """
    Compute a stable dedup hash for a sheet row.
    Parsed rows (with name/address/emails) hash by those fields.
    Unparsed rows hash by (sent_date, truncated content).
    """
    date = row[0] if len(row) > 0 else ""
    name = row[1] if len(row) > 1 else ""
    address = row[2] if len(row) > 2 else ""
    email_1 = row[3] if len(row) > 3 else ""
    email_2 = row[4] if len(row) > 4 else ""
    content = row[5] if len(row) > 5 else ""
    if any((name, address, email_1, email_2)):
        return _parsed_hash(date, name, address, email_1, email_2)
    return _unparsed_hash(date, content, content_limit)


def get_existing_hashes(
    creds: Credentials,
    spreadsheet_id: str,
    sheet_name: str,
    content_limit: int,
) -> set[str]:
    """Return hashes of all data rows already on the sheet (skips header row)."""
    service = build("sheets", "v4", credentials=creds)
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"'{sheet_name}'!A:J")
            .execute()
        )
    except HttpError:
        return set()
    rows = result.get("values", [])
    return {row_hash(r, content_limit) for r in rows[1:]}


def append_rows(
    creds: Credentials,
    spreadsheet_id: str,
    sheet_name: str,
    rows: list[tuple],
    content_limit: int,
) -> None:
    """
    Append rows to the sheet.

    Each row is (sent_date, name, address, email_1, email_2, content,
    nearest_charger, distance_mi, hubspot_contact, hubspot_email).
    Prepends a header row if the sheet is currently empty.
    """
    service = build("sheets", "v4", credentials=creds)
    range_name = f"'{sheet_name}'!A:J"

    try:
        existing = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"'{sheet_name}'!A1:J1")
            .execute()
        )
        has_header = bool(existing.get("values"))
    except HttpError:
        has_header = False

    def _fmt(r: tuple) -> list:
        sd, nm, addr, e1, e2, body, nc, dm, hs_contact, hs_email = r
        return [sd, nm, addr, e1, e2, truncate(body, content_limit), nc, dm, hs_contact, hs_email]

    data = [_fmt(r) for r in rows]
    if not data:
        return

    body: dict = {"values": data}
    if not has_header:
        body["values"] = [COLUMNS] + body["values"]

    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()
    print(f"Appended {len(data)} row(s) to sheet '{sheet_name}'.")
