import argparse
import base64
import hashlib
import os.path
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

def decode_base64(message_bytes):
  return base64.urlsafe_b64decode(message_bytes).decode("utf-8")


def extract_field(json_data, field_name, default=None):
  headers = json_data.get("payload", {}).get("headers", [])
  return next((h["value"] for h in headers if h["name"] == field_name), default)


def get_body_from_payload(payload):
  """
  Get decoded body text from a Gmail message payload.
  Handles single-part messages (body in payload.body), multipart, and
  nested multipart (e.g. multipart/alternative). Prefers text/html when both exist.
  Returns (mime_type, decoded_str) or (None, None) if no body.
  """
  # Single-part: no parts or empty parts — body is in payload.body
  parts = payload.get("parts") or []
  if not parts:
    body = payload.get("body") or {}
    data = body.get("data")
    if data:
      mime = payload.get("mimeType", "text/plain")
      return (mime, decode_base64(data))
    return (None, None)

  # Multipart: collect (mimeType, data) from leaf parts (recurse into nested multipart)
  candidates = []

  def collect_parts(part):
    body = part.get("body") or {}
    data = body.get("data")
    subparts = part.get("parts") or []
    if data:
      mime = part.get("mimeType", "text/plain")
      candidates.append((mime, decode_base64(data)))
    for p in subparts:
      collect_parts(p)

  for part in parts:
    collect_parts(part)

  if not candidates:
    return (None, None)
  # Prefer text/html, then text/plain, then first available
  for mime in ("text/html", "text/plain"):
    for (m, text) in candidates:
      if m == mime:
        return (m, text)
  return candidates[0]


def html_to_plain_text(html_str):
  """
  Convert HTML email body to plain text using BeautifulSoup.
  Strips tags and normalizes whitespace for easier string extraction.
  """
  soup = BeautifulSoup(html_str, "html.parser")
  text = soup.get_text(separator=" ", strip=True)
  # Collapse runs of whitespace/newlines to a single space
  return re.sub(r"\s+", " ", text).strip()


def body_to_plain_text(mime_type, body_str):
  """
  Return plain text from a message body. If mime_type is text/html,
  parse with BeautifulSoup; otherwise return the string as-is.
  """
  if mime_type and mime_type.lower() == "text/html":
    return html_to_plain_text(body_str)
  return body_str


def format_sent_date(msg_response):
  """
  Return a human-readable sent date from a Gmail message response.
  Uses internalDate (epoch ms); falls back to Date header if present.
  """
  internal = msg_response.get("internalDate")
  if internal:
    try:
      ts = int(internal) / 1000
      return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, TypeError):
      pass
  payload = msg_response.get("payload", {})
  date_header = extract_field(payload, "Date")
  return date_header or ""


def _truncate_content(s, limit):
  """Normalize and truncate content for sheet cell or hashing. Same logic in both places."""
  if s is None:
    return ""
  s = str(s).strip()
  if len(s) <= limit:
    return s
  return s[: limit - 3] + "..."


def _row_hash(sent_date, content, content_limit):
  """Stable hash for (sent_date, truncated content) so we can dedupe against sheet rows."""
  key = (str(sent_date).strip() + "\n" + _truncate_content(content, content_limit)).encode("utf-8")
  return hashlib.sha256(key).hexdigest()


def get_existing_row_hashes(creds, spreadsheet_id, sheet_name, content_limit):
  """
  Fetch all data rows from the sheet (skip header) and return a set of row hashes.
  Used to avoid appending rows that are already present.
  """
  service = build("sheets", "v4", credentials=creds)
  range_name = f"'{sheet_name}'!A:B"
  try:
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
    )
  except HttpError:
    return set()
  values = result.get("values", [])
  # Skip header row (first row)
  data_rows = values[1:] if len(values) > 1 else []
  existing = set()
  for row in data_rows:
    date_cell = row[0] if len(row) > 0 else ""
    content_cell = row[1] if len(row) > 1 else ""
    existing.add(_row_hash(date_cell, content_cell, content_limit))
  return existing


def append_rows_to_sheet(creds, spreadsheet_id, sheet_name, rows, content_limit):
  """
  Append rows to a Google Sheet. First column = sent date, second = content.
  If the sheet is empty, prepends a header row. Truncates content to content_limit chars.
  """
  service = build("sheets", "v4", credentials=creds)
  range_name = f"'{sheet_name}'!A:B"

  # Optionally add header if sheet is empty
  try:
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"'{sheet_name}'!A1:B1")
        .execute()
    )
    values = result.get("values", [])
    has_header = bool(values)
  except HttpError:
    has_header = False

  data_rows = []
  for sent_date, content in rows:
    data_rows.append([sent_date, _truncate_content(content, content_limit)])

  if not data_rows:
    return

  body = {"values": data_rows}
  if not has_header:
    body["values"] = [["Sent Date", "Content"]] + body["values"]

  (
      service.spreadsheets()
      .values()
      .append(
          spreadsheetId=spreadsheet_id,
          range=range_name,
          valueInputOption="USER_ENTERED",
          insertDataOption="INSERT_ROWS",
          body=body,
      )
      .execute()
  )
  print(f"Appended {len(data_rows)} row(s) to sheet '{sheet_name}'.")


def parse_args():
  parser = argparse.ArgumentParser(
      description="Fetch messages from Gmail by label and show body previews.",
  )
  parser.add_argument(
      "--label",
      default="INBOX",
      help="Gmail label name to list messages from (e.g. INBOX, Follow Up). Default: INBOX",
  )
  parser.add_argument(
      "--max-messages",
      type=int,
      default=10,
      metavar="N",
      help="Maximum number of messages to fetch. Default: 10",
  )
  parser.add_argument(
      "--body-length",
      type=int,
      default=200,
      metavar="N",
      help="Max characters of body text to print per message (0 = no limit). Default: 200",
  )
  parser.add_argument(
      "--spreadsheet-id",
      metavar="ID",
      help="Google Spreadsheet ID to append rows to (from the sheet URL). If set, each message is written as a row with sent date and parsed content.",
  )
  parser.add_argument(
      "--sheet",
      default="Sheet1",
      metavar="NAME",
      help="Sheet (tab) name within the spreadsheet. Default: Sheet1",
  )
  parser.add_argument(
      "--content-limit",
      type=int,
      default=5000,
      metavar="N",
      help="Max characters of content per cell when writing to Sheets (cell limit 50k). Default: 50000",
  )
  return parser.parse_args()


def main():
  args = parse_args()

  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    print("Token file exists")
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      print("No valid credentials available, creating new ones")
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      print("Saving credentials to token.json")
      token.write(creds.to_json())

  try:
    # Call the Gmail API
    print("Calling Gmail API")
    service = build("gmail", "v1", credentials=creds)
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])

    if not labels:
      print("No labels found.")
      return

    label_id = None
    for label in labels:
      if label["name"] == args.label:
        label_id = label["id"]
        break
    if not label_id:
      print(f"Label '{args.label}' not found.")
      return
    print(f"Label '{args.label}' ID: {label_id}")

    messages = service.users().messages().list(
        userId="me",
        labelIds=[label_id],
        maxResults=args.max_messages,
    ).execute()
    message_ids = [m["id"] for m in messages.get("messages", [])]
    print("Message IDs:", message_ids)

    sheet_rows = []
    for message_id in message_ids:
      msg_response = service.users().messages().get(userId="me", id=message_id).execute()
      payload = msg_response.get("payload", {})

      sent_date = format_sent_date(msg_response)
      mime_type, body_text = get_body_from_payload(payload)
      plain = None
      if body_text is not None:
        plain = body_to_plain_text(mime_type, body_text)
        if args.body_length and len(plain) > args.body_length:
          body_preview = plain[: args.body_length] + "..."
        else:
          body_preview = plain
        print(f"[plain]:", body_preview)
      else:
        print("No body found for message.")

      if args.spreadsheet_id:
        sheet_rows.append((sent_date, plain or ""))

    if args.spreadsheet_id and sheet_rows:
      existing_hashes = get_existing_row_hashes(
          creds,
          args.spreadsheet_id,
          args.sheet,
          args.content_limit,
      )
      new_rows = [
          (sent_date, content)
          for sent_date, content in sheet_rows
          if _row_hash(sent_date, content, args.content_limit) not in existing_hashes
      ]
      skipped = len(sheet_rows) - len(new_rows)
      if skipped:
        print(f"Skipping {skipped} row(s) already on sheet.")
      if new_rows:
        append_rows_to_sheet(
            creds,
            args.spreadsheet_id,
            args.sheet,
            new_rows,
            args.content_limit,
        )
      elif not new_rows and sheet_rows:
        print("All fetched messages already exist on the sheet; nothing to append.")

  except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  main()