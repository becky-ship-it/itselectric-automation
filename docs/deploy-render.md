# Deploying to Render

The app ships as a Docker image (multi-stage: Node builds the frontend, Python
runs the server) backed by a managed Postgres database. Configuration lives in
[`render.yaml`](../render.yaml) as a Render Blueprint.

## What Render creates

| Resource | From |
|----------|------|
| Web service `itselectric` | `Dockerfile`, serves the API + built frontend on `$PORT` |
| Postgres `itselectric-db` | `databases:` block; `DATABASE_URL` is injected automatically |

The server reads `DATABASE_URL` and rewrites the scheme to the `psycopg`
dialect, so no code change is needed between local SQLite and hosted Postgres.

## One-time deploy

1. Push this branch to the default branch (or point the Blueprint at it).
2. In Render: **New → Blueprint**, pick this repo. Render reads `render.yaml`
   and provisions the web service and the database.
3. Set the three Google env vars (below) in the service's **Environment** tab.
4. Deploy.

Health check: `GET /api/config` (returns current config JSON).

## Google / Gmail setup (the important part)

The server never opens a browser. It builds OAuth credentials from three
environment variables and refreshes them automatically. You mint the refresh
token **once, locally**, using your existing Google Cloud OAuth client.

### 1. Download the OAuth client secret

Google Cloud Console → **APIs & Services → Credentials** → your OAuth client →
**Download JSON**. It must be a **Desktop app** client, or a **Web application**
client with `http://localhost` added as an authorized redirect URI, so the
local consent step can complete.

### 2. Mint a refresh token locally

```bash
uv run python scripts/authorize_google.py path/to/client_secret.json
```

A browser opens; sign in with the Google account that owns the Gmail inbox and
grant the scopes. The script prints:

```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...
```

### 3. Set them on Render

Paste all three into the service's **Environment** tab (they are marked
`sync: false` in `render.yaml`, so they are never committed). Redeploy.

The server calls `_credentials_from_env()` first; when all three are present it
uses them and skips the file/browser flow entirely.

### Keep the refresh token alive

If your OAuth **consent screen is in "Testing"** mode, Google expires refresh
tokens after **7 days** and the server breaks weekly. Set the consent screen's
publishing status to **In production** (OAuth consent screen → Publish app).
For a single internal user this needs no Google verification review and stops
the weekly expiry.

If the token is ever revoked or expired, re-run step 2 and update
`GOOGLE_REFRESH_TOKEN`.

## Local development is unchanged

With the three `GOOGLE_*` env vars unset, `get_credentials()` falls back to the
original file-based flow (`credentials.json` → browser consent → `token.json`),
and the default `DATABASE_URL` is local SQLite. Nothing about `run_server.sh`
changes.
