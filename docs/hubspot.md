# HubSpot Integration

When `hubspot_access_token` is set in config, the pipeline creates or updates a contact in HubSpot CRM for every parsed email. Uses the [batch upsert endpoint](https://developers.hubspot.com/docs/api-reference/crm-contacts-v3/guide) with email as the dedup key — re-running updates existing contacts rather than creating duplicates.

## Getting an access token

1. In HubSpot, go to **Development → Legacy Apps** and open your app.
2. Navigate to the **Auth** tab and copy the **Access token**.
3. Set it in the web UI at `/config` → `hubspot_access_token`.

## What gets synced

| HubSpot property | Source |
|-----------------|--------|
| `email` | `email_1` (from Gmail headers) |
| `firstname` | First word of extracted `name` |
| `lastname` | Remaining words of extracted `name` |
| `address` | Street portion of extracted address |
| `city` | City parsed from address |
| `state` | State parsed from address |
| `zip` | ZIP code parsed from address |
| `form_selection` | Always `"EV Driver"` (custom property) |

Address is split automatically from the contact's extracted address string (e.g. `"123 Main St, Brooklyn, NY 11205"` → street + city + state + zip).

Only **parsed** emails are synced. Unparsed emails are skipped. When a contact is manually fixed via the Inbox UI, HubSpot is not automatically re-synced — run the pipeline again or trigger via the API if needed.

## Behaviour

- **Non-fatal** — if the API call fails, the pipeline logs the error and continues. The contact's `hubspot_status` field is set to `"synced"` or `"failed"`.
- **Idempotent** — re-running updates existing contacts rather than creating duplicates.
- All properties are always sent (partial upserts are not supported when using email as the dedup key).
