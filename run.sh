#!/usr/bin/env bash
# Setup Python environment and run itselectric-automation.
# Run from repo root: ./run.sh [SPREADSHEET_ID] [LABEL]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="${VENV_DIR:-venv}"
PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" &>/dev/null; then
  echo "Error: $PYTHON not found. Install Python 3 and try again."
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment in $VENV_DIR..."
  "$PYTHON" -m venv "$VENV_DIR"
else
  echo "Using existing virtual environment: $VENV_DIR"
fi

echo "Activating venv and installing dependencies..."
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if [[ -f credentials.json ]]; then
  echo ""
  SPREADSHEET_ID="${1:-}"
  LABEL="${2:-}"
  ARGS=()
  [[ -n "$SPREADSHEET_ID" ]] && ARGS+=(--spreadsheet-id "$SPREADSHEET_ID")
  [[ -n "$LABEL" ]] && ARGS+=(--label "$LABEL")
  if [[ ${#ARGS[@]} -gt 0 ]]; then
    echo "credentials.json found. Running script with: ${ARGS[*]}"
  else
    echo "credentials.json found. Running script (preview only; pass spreadsheet ID and/or label to customize)."
  fi
  python test_script.py "${ARGS[@]}"
else
  echo ""
  echo "Setup complete. Add credentials.json (OAuth client config from Google Cloud Console),"
  echo "then run again. Optional arguments: spreadsheet ID, Gmail label (e.g. INBOX, \"Follow Up\"):"
  echo "  ./run.sh [SPREADSHEET_ID] [LABEL]"
fi
