#!/usr/bin/env bash
# Build the Email Sheets macOS .app bundle using PyInstaller.
# Run from repo root: ./build_app.sh
#
# Output: dist/Email Sheets.app
# Then drag to /Applications or double-click from dist/.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Installing dependencies (including PyInstaller)..."
uv sync --extra dev

echo ""
echo "Building Email Sheets.app..."
uv run pyinstaller EmailSheets.spec --noconfirm

echo ""
echo "✅ Build complete: dist/Email Sheets.app"
echo ""
echo "To install: drag 'dist/Email Sheets.app' to your /Applications folder."
echo "First launch: right-click → Open → Open Anyway (macOS Gatekeeper)."
echo ""
echo "Put your config.yaml and credentials.json in the same folder."
echo "Browse for config.yaml in the app to get started."
