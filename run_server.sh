#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Expand PATH for non-login shells (launchd, cron) that skip ~/.zshrc
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# ── Python deps via uv ───────────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
  echo "Error: uv required. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

echo "Syncing Python dependencies..."
uv sync

# ── Node / frontend ─────────────────────────────────────────────────────────
if ! command -v node &>/dev/null; then
  echo "Error: Node.js required. Install from https://nodejs.org/"
  exit 1
fi

cd "$PROJECT_DIR/web"

echo "Installing Node dependencies..."
npm install --silent

echo "Building frontend..."
npm run build --silent

cd "$PROJECT_DIR"

# ── Launch ───────────────────────────────────────────────────────────────────
mkdir -p data

echo "Server starting at http://localhost:8000"
exec uv run uvicorn server.main:app --host 0.0.0.0 --port 8000
