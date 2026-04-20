#!/bin/bash
set -e

if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

mkdir -p data

echo "Starting It's Electric server at http://localhost:8000"
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
