"""CLI entry point for It's Electric Gmail-to-Sheets automation."""

import argparse

from googleapiclient.errors import HttpError

from .auth import get_credentials
from .extract import extract_parsed
from .gmail import body_to_plain, fetch_messages, format_sent_date, get_body_from_payload
from .sheets import append_rows, get_existing_hashes, row_hash


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Gmail messages by label and record extracted data in a Google Sheet.",
    )
    parser.add_argument(
        "--label",
        default="INBOX",
        help="Gmail label name to list messages from (e.g. INBOX, Follow Up). Default: INBOX",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=100,
        metavar="N",
        help="Maximum number of messages to fetch. Default: 100",
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
        help="Google Spreadsheet ID to append rows to (from the sheet URL).",
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
        help="Max characters of content per cell when writing to Sheets. Default: 5000",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    creds = get_credentials()

    try:
        messages = fetch_messages(creds, args.label, args.max_messages)
    except HttpError as e:
        print(f"Gmail API error: {e}")
        return

    sheet_rows = []
    for msg in messages:
        sent_date = format_sent_date(msg)
        mime_type, body_text = get_body_from_payload(msg.get("payload", {}))

        plain = None
        if body_text is not None:
            plain = body_to_plain(mime_type, body_text)
            over = args.body_length and len(plain) > args.body_length
            preview = plain[: args.body_length] + "..." if over else plain
            print(f"[plain]: {preview}")
        else:
            print("No body found for message.")

        if args.spreadsheet_id:
            content = plain or ""
            parsed = extract_parsed(content)
            if parsed:
                sheet_rows.append((
                    sent_date,
                    parsed["name"],
                    parsed["address"],
                    parsed["email_1"],
                    parsed["email_2"],
                    content,
                ))
            else:
                sheet_rows.append((sent_date, "", "", "", "", content))

    if args.spreadsheet_id and sheet_rows:
        try:
            existing = get_existing_hashes(
                creds, args.spreadsheet_id, args.sheet, args.content_limit
            )

            def _hash(r):
                sent_date, name, address, email_1, email_2, content = r
                return row_hash(
                    [sent_date, name, address, email_1, email_2, content],
                    args.content_limit,
                )

            new_rows = [r for r in sheet_rows if _hash(r) not in existing]
            skipped = len(sheet_rows) - len(new_rows)
            if skipped:
                print(f"Skipping {skipped} row(s) already on sheet.")
            if new_rows:
                append_rows(creds, args.spreadsheet_id, args.sheet, new_rows, args.content_limit)
            else:
                print("All fetched messages already exist on the sheet; nothing to append.")
        except HttpError as e:
            print(f"Sheets API error: {e}")


if __name__ == "__main__":
    main()
