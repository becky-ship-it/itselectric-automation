#!/usr/bin/env bash
# Setup Python environment and run itselectric-automation.
# Run from repo root: ./run.sh [SPREADSHEET_ID] [LABEL]
#
# Prefers uv if available; falls back to a plain venv.
# Settings in config.yaml are picked up automatically.
# CLI args override config.yaml when provided.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SPREADSHEET_ID="${1:-}"
LABEL="${2:-}"
ARGS=()
[[ -n "$SPREADSHEET_ID" ]] && ARGS+=(--spreadsheet-id "$SPREADSHEET_ID")
[[ -n "$LABEL" ]] && ARGS+=(--label "$LABEL")

if command -v uv &>/dev/null; then
  echo "Using uv..."
  uv sync --quiet
  if [[ -f credentials.json ]]; then
    if [[ ${#ARGS[@]} -gt 0 ]]; then
      echo "Running with: ${ARGS[*]}"
    else
      echo "Running with settings from config.yaml (preview only if no spreadsheet_id set)."
    fi
    uv run itselectric "${ARGS[@]}"
  else
    echo "Setup complete. Add credentials.json (OAuth client config from Google Cloud Console) and run again."
  fi
else
  # Fallback: plain venv
  VENV_DIR="${VENV_DIR:-venv}"
  PYTHON="${PYTHON:-python3}"

  if ! command -v "$PYTHON" &>/dev/null; then
    echo "Error: $PYTHON not found. Install Python 3 or uv and try again."
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
  pip install --quiet -e .

  if [[ -f credentials.json ]]; then
    if [[ ${#ARGS[@]} -gt 0 ]]; then
      echo "Running with: ${ARGS[*]}"
    else
      echo "Running with settings from config.yaml (preview only if no spreadsheet_id set)."
    fi
    python -m itselectric.cli "${ARGS[@]}"
  else
    echo "Setup complete. Add credentials.json (OAuth client config from Google Cloud Console) and run again."
  fi
fi
