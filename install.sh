#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="GitLab Tracker"
BUNDLE_ID="com.acg.gitlab-contribution-tracker"
INSTALL_DIR="$HOME/Applications"
LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="${BUNDLE_ID}.plist"

echo "=== GitLab Contribution Tracker - Install ==="
echo ""

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Please install Python 3."
    exit 1
fi

echo "[1/5] Creating virtual environment..."
cd "$SCRIPT_DIR"
python3 -m venv .venv
source .venv/bin/activate

echo "[2/5] Installing dependencies..."
pip install --quiet -r requirements.txt

echo "[3/5] Building macOS application..."
python setup.py py2app --no-strip 2>/dev/null || python setup.py py2app

echo "[4/5] Installing application..."
mkdir -p "$INSTALL_DIR"

if [ -d "$INSTALL_DIR/${APP_NAME}.app" ]; then
    echo "  Removing previous version..."
    rm -rf "$INSTALL_DIR/${APP_NAME}.app"
fi

cp -R "dist/${APP_NAME}.app" "$INSTALL_DIR/"
echo "  Application: $INSTALL_DIR/${APP_NAME}.app"

echo "[5/5] Setting up auto-start..."
mkdir -p "$LAUNCH_AGENT_DIR"

APP_EXECUTABLE="$INSTALL_DIR/${APP_NAME}.app/Contents/MacOS/${APP_NAME}"
sed "s|__APP_PATH__|${APP_EXECUTABLE}|g" "$SCRIPT_DIR/$PLIST_NAME" > "$LAUNCH_AGENT_DIR/$PLIST_NAME"

launchctl unload "$LAUNCH_AGENT_DIR/$PLIST_NAME" 2>/dev/null || true
launchctl load "$LAUNCH_AGENT_DIR/$PLIST_NAME"

echo ""
echo "=== Installation complete! ==="
echo ""
echo "  Starting application..."
open "$INSTALL_DIR/${APP_NAME}.app"
echo ""
echo "  You should see the ⬆ icon in your menu bar."
echo "  The app will start automatically on login."
echo ""
echo "  To uninstall: ./uninstall.sh"
