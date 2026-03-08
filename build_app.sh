#!/usr/bin/env bash
# Build the it's electric automation macOS .app bundle using PyInstaller.
# Run from repo root: ./build_app.sh
#
# Output: dist/it's electric automation.app
# Then drag to /Applications or double-click from dist.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Require uv
if ! command -v uv &>/dev/null; then
  echo "Error: uv is required. Install it with:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

# Ensure uv's managed Python 3.12 is installed (includes Tcl/Tk — required for tkinter/customtkinter)
echo "Ensuring Python 3.12 (managed by uv, includes Tcl/Tk)..."
uv python install 3.12

echo "Installing dependencies (including PyInstaller)..."
uv sync --extra dev

# Verify tkinter is available before attempting to build
echo "Verifying tkinter..."
if ! uv run python -c "import tkinter" 2>/dev/null; then
  echo ""
  echo "Error: tkinter is not available in the build Python."
  echo "This usually means uv picked up a system Python instead of its managed one."
  echo "Try removing the .venv and re-running:"
  echo "  rm -rf .venv && ./build_app.sh"
  exit 1
fi
echo "tkinter ok."

echo ""
echo "Building it's electric automation.app..."
uv run pyinstaller app.spec --noconfirm

echo ""
echo "✅ Build complete: dist/it's electric automation.app"
echo ""
echo "To install: drag 'dist/it's electric automation.app' to your /Applications folder."
echo "First launch: right-click → Open → Open Anyway (macOS Gatekeeper)."
echo ""
echo "Put your config.yaml and credentials.json in the same folder."
echo "Browse for config.yaml in the app to get started."
