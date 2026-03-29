"""HubSpot CRM helpers: upsert contacts via the v3 batch API."""

import requests

_BASE = "https://api.hubapi.com"


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def _split_name(name: str) -> tuple[str, str]:
    """Split 'First Last' into ('First', 'Last'). Single word → ('Word', '')."""
    parts = name.strip().split(" ", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def upsert_contact(
    access_token: str,
    name: str,
    email: str,
    address: str,
) -> str | None:
    """
    Create or update a HubSpot contact using the batch upsert endpoint.
    Uses email as the dedup key (idProperty). All properties are always sent
    since partial upserts are not supported with email as idProperty.
    Returns the contact ID, or None on error.
    """
    firstname, lastname = _split_name(name)
    try:
        resp = requests.post(
            f"{_BASE}/crm/v3/objects/contacts/batch/upsert",
            headers=_headers(access_token),
            json={
                "inputs": [
                    {
                        "id": email,
                        "idProperty": "email",
                        "properties": {
                            "email": email,
                            "firstname": firstname,
                            "lastname": lastname,
                            "address": address,
                        },
                    }
                ]
            },
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0]["id"] if results else None
    except requests.RequestException as e:
        print(f"HubSpot API error: {e}")
        return None
