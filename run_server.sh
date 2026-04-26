#!/bin/bash
set -e

# Resolve the project root regardless of where this script is called from
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Ensure Python 3.10+
PYTHON=$(command -v python3.12 || command -v python3.11 || command -v python3.10 || command -v python3 || true)
if [ -z "$PYTHON" ]; then
  echo "Error: Python 3.10+ required. Install from https://www.python.org/downloads/"
  exit 1
fi

# Bootstrap venv if missing
if [ ! -f ".venv/bin/activate" ]; then
  echo "Creating virtual environment..."
  "$PYTHON" -m venv .venv
fi

source .venv/bin/activate

# Install/sync dependencies
echo "Checking dependencies..."
pip install -q -e ".[dev]" 2>&1 | grep -v "^Requirement already"

mkdir -p data

echo "Server starting at http://localhost:8000"
exec uvicorn server.main:app --host 0.0.0.0 --port 8000
