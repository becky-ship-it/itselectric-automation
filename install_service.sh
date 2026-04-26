#!/bin/bash
# Installs the It's Electric server as a macOS LaunchAgent so it starts on login.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_LABEL="com.itselectric.server"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"
LOG_PATH="$HOME/Library/Logs/itselectric-server.log"

# Unload existing service if present
if launchctl list | grep -q "$PLIST_LABEL" 2>/dev/null; then
  echo "Stopping existing service..."
  launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$HOME/Library/Logs"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${SCRIPT_DIR}/run_server.sh</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${SCRIPT_DIR}</string>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>${LOG_PATH}</string>
  <key>StandardErrorPath</key>
  <string>${LOG_PATH}</string>
</dict>
</plist>
PLIST

echo "Loading service..."
launchctl load "$PLIST_PATH"

echo ""
echo "Done. Service registered as: $PLIST_LABEL"
echo "  Status : launchctl list | grep itselectric"
echo "  Logs   : tail -f $LOG_PATH"
echo "  Stop   : launchctl unload $PLIST_PATH"
echo "  Start  : launchctl load $PLIST_PATH"
