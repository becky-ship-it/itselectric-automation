"""CLI entry point for It's Electric Gmail-to-Sheets automation."""

import argparse
import os

import yaml  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

from .auth import get_credentials
from .decision_tree import evaluate as evaluate_tree
from .extract import extract_parsed
from .fixture import load_fixture_messages
from .geo import (
    DEFAULT_CHARGERS_CSV,
    extract_state_from_address,
    find_nearest_charger,
    geocode_address,
    load_chargers,
)
from .gmail import body_to_plain, fetch_messages, format_sent_date, get_body_from_payload
from .hubspot import send_email, upsert_contact
from .sheets import append_rows, get_existing_hashes, row_hash

CONFIG_FILE = "config.yaml"

_DEFAULTS = {
    "label": "INBOX",
    "max_messages": 100,
    "body_length": 200,
    "spreadsheet_id": "",
    "sheet": "Sheet1",
    "content_limit": 5000,
    "chargers": str(DEFAULT_CHARGERS_CSV),
    "geocache": "geocache.json",
    "fixture_dir": "",
    "hubspot_access_token": "",
    "decision_tree_file": "",
}


def _load_decision_tree(path: str) -> dict | None:
    """Load and return the decision tree dict from a YAML file, or None if path is empty/missing."""
    if not path:
        return None
    if not os.path.exists(path):
        print(f"Warning: decision_tree_file not found at '{path}'; email routing disabled.")
        return None
    with open(path) as f:
        return yaml.safe_load(f)


def _build_tree_context(address: str, charger_dict: dict, distance_miles: float) -> dict:
    """Build the context dict passed to the decision tree evaluator."""
    return {
        "driver_state": extract_state_from_address(address),
        "charger_state": charger_dict["state"],
        "charger_city": charger_dict["city"],
        "distance_miles": distance_miles,
    }


def _load_config(path: str = CONFIG_FILE) -> dict:
    """Load config.yaml if present, returning a dict merged over defaults."""
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    print(f"Loaded config from {path}")
    return data


def parse_args(config: dict) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Gmail messages by label and record extracted data in a Google Sheet.",
    )
    parser.add_argument(
        "--label",
        default=config.get("label", _DEFAULTS["label"]),
        help="Gmail label name to list messages from (e.g. INBOX, Follow Up).",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=config.get("max_messages", _DEFAULTS["max_messages"]),
        metavar="N",
        help="Maximum number of messages to fetch.",
    )
    parser.add_argument(
        "--body-length",
        type=int,
        default=config.get("body_length", _DEFAULTS["body_length"]),
        metavar="N",
        help="Max characters of body text to print per message (0 = no limit).",
    )
    parser.add_argument(
        "--spreadsheet-id",
        default=config.get("spreadsheet_id", _DEFAULTS["spreadsheet_id"]),
        metavar="ID",
        help="Google Spreadsheet ID to append rows to (from the sheet URL).",
    )
    parser.add_argument(
        "--sheet",
        default=config.get("sheet", _DEFAULTS["sheet"]),
        metavar="NAME",
        help="Sheet (tab) name within the spreadsheet.",
    )
    parser.add_argument(
        "--content-limit",
        type=int,
        default=config.get("content_limit", _DEFAULTS["content_limit"]),
        metavar="N",
        help="Max characters of content per cell when writing to Sheets.",
    )
    parser.add_argument(
        "--chargers",
        default=config.get("chargers", _DEFAULTS["chargers"]),
        metavar="PATH",
        help=(
            "Path to chargers CSV (columns: STREET,CITY,STATE,LAT,LONG,LAT_OVERRIDE,LONG_OVERRIDE)."
        ),
    )
    parser.add_argument(
        "--geocache",
        default=config.get("geocache", _DEFAULTS["geocache"]),
        metavar="PATH",
        help="Path to JSON file for caching geocoded addresses.",
    )
    parser.add_argument(
        "--fixture-dir",
        default=config.get("fixture_dir", _DEFAULTS["fixture_dir"]),
        metavar="DIR",
        help="Load emails from .txt files in this directory instead of Gmail. Auth is still"
        " required when --spreadsheet-id is set.",
    )
    parser.add_argument(
        "--hubspot-access-token",
        default=config.get("hubspot_access_token", _DEFAULTS["hubspot_access_token"]),
        metavar="TOKEN",
        help="HubSpot Private App access token. When set, creates/updates contacts in HubSpot.",
    )
    parser.add_argument(
        "--decision-tree-file",
        default=config.get("decision_tree_file", _DEFAULTS["decision_tree_file"]),
        metavar="PATH",
        help="Path to YAML file defining the email routing decision tree.",
    )
    return parser.parse_args()


def main() -> None:
    config = _load_config()
    args = parse_args(config)
    try:
        chargers = load_chargers(args.chargers)
        print(f"Loaded {len(chargers)} charger(s) from {args.chargers}")
    except FileNotFoundError:
        print(f"Warning: chargers file not found at '{args.chargers}'; proximity lookup disabled.")
        chargers = []

    decision_tree = _load_decision_tree(args.decision_tree_file)

    if args.fixture_dir:
        print(f"Using fixture directory: {args.fixture_dir}")
        try:
            messages = load_fixture_messages(args.fixture_dir)
        except FileNotFoundError as e:
            print(f"Fixture directory not found: {e}")
            return
        # Still need credentials when writing to a sheet, even in fixture mode.
        creds = get_credentials() if args.spreadsheet_id else None
    else:
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

        content = plain or ""
        parsed = extract_parsed(content)

        contact_status = ""
        email_status = ""

        if parsed and args.hubspot_access_token:
            contact_id = upsert_contact(
                access_token=args.hubspot_access_token,
                name=parsed["name"],
                email=parsed["email_1"],
                address=parsed["address"],
            )
            contact_status = "created" if contact_id else "failed"
            if contact_id:
                print(f"  → HubSpot contact: {contact_id}")
            else:
                print("  → HubSpot upsert failed (see error above).")

        # Geocode outside the sheets gate — decision tree also needs charger proximity.
        nearest_charger_dict = None
        nearest_charger = ""
        distance_mi = ""
        dist_float = None

        if parsed and chargers:
            coords = geocode_address(parsed["address"], cache_path=args.geocache)
            if coords:
                lat, lon = coords
                result = find_nearest_charger(lat, lon, chargers)
                if result:
                    nearest_charger_dict, dist_float = result
                    nearest_charger = nearest_charger_dict["name"]
                    distance_mi = str(dist_float)
                    print(f"  → Nearest charger: {nearest_charger} ({distance_mi} mi)")
            else:
                print(f"  → Could not geocode: {parsed['address']!r}")

        if (
            decision_tree
            and nearest_charger_dict
            and dist_float
            and parsed
            and args.hubspot_access_token
        ):
            ctx = _build_tree_context(
                address=parsed["address"],
                charger_dict=nearest_charger_dict,
                distance_miles=dist_float,
            )
            try:
                email_id = evaluate_tree(decision_tree, ctx)
            except (KeyError, ValueError) as e:
                print(f"  → Decision tree error: {e}")
                email_id = None
            if email_id is not None:
                sent = send_email(
                    access_token=args.hubspot_access_token,
                    to_email=parsed["email_1"],
                    email_id=email_id,
                )
                email_status = "sent" if sent else "failed"
                print(
                    f"""  → Email template {email_id} """
                    f"""{'sent' if sent else 'FAILED'} → {parsed['email_1']}"""
                )

        if args.spreadsheet_id:
            if parsed:
                sheet_rows.append(
                    (
                        sent_date,
                        parsed["name"],
                        parsed["address"],
                        parsed["email_1"],
                        parsed["email_2"],
                        content,
                        nearest_charger,
                        distance_mi,
                        contact_status,
                        email_status,
                    )
                )
            else:
                sheet_rows.append((sent_date, "", "", "", "", content, "", "", "", ""))

    if args.spreadsheet_id and sheet_rows:
        if not creds:
            print("Error: credentials required to write to Sheets.")
            return
        try:
            existing = get_existing_hashes(
                creds, args.spreadsheet_id, args.sheet, args.content_limit
            )

            new_rows = [r for r in sheet_rows if row_hash(list(r), args.content_limit) not in existing]
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
