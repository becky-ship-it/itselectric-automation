# HubSpot Integration

When `hubspot_access_token` is set, the pipeline creates or updates a contact in HubSpot CRM for every parsed email. Uses the [batch upsert endpoint](https://developers.hubspot.com/docs/api-reference/crm-contacts-v3/guide) with email as the dedup key — re-running updates existing contacts rather than creating duplicates.

HubSpot and Sheets are independent — you can set one, both, or neither.

## Getting an access token

1. In HubSpot, go to **Development → Legacy Apps** and open your app.
2. Navigate to the **Auth** tab and copy the **Access token**.
3. Add it to `config.yaml`:

```yaml
hubspot_access_token: "your-token-here"
```

## What gets synced

| HubSpot property | Source |
|-----------------|--------|
| `email` | `email_1` (from Gmail headers) |
| `firstname` | First word of extracted `name` |
| `lastname` | Remaining words of extracted `name` |
| `address` | Extracted `address` |

Only **parsed** emails (those matching the extraction regex) are synced. Unparsed emails are skipped.

## Behaviour

- **Non-fatal** — if the API call fails, the pipeline prints the error and continues.
- **Idempotent** — re-running the pipeline updates existing contacts rather than creating duplicates.
- All four properties are always sent (partial upserts are not supported when using email as the dedup key).
