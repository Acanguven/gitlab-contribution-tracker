#!/bin/bash
set -e

APP_NAME="GitLab Tracker"
BUNDLE_ID="com.acg.gitlab-contribution-tracker"
INSTALL_DIR="$HOME/Applications"
LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="${BUNDLE_ID}.plist"

echo "=== GitLab Contribution Tracker - Uninstall ==="
echo ""

echo "[1/3] Removing auto-start..."
if [ -f "$LAUNCH_AGENT_DIR/$PLIST_NAME" ]; then
    launchctl unload "$LAUNCH_AGENT_DIR/$PLIST_NAME" 2>/dev/null || true
    rm -f "$LAUNCH_AGENT_DIR/$PLIST_NAME"
    echo "  LaunchAgent removed."
else
    echo "  LaunchAgent not found, skipping."
fi

echo "[2/3] Removing application..."
if [ -d "$INSTALL_DIR/${APP_NAME}.app" ]; then
    pkill -f "${APP_NAME}" 2>/dev/null || true
    sleep 1
    rm -rf "$INSTALL_DIR/${APP_NAME}.app"
    echo "  Application removed."
else
    echo "  Application not found, skipping."
fi

echo "[3/3] Configuration files..."
CONFIG_DIR="$HOME/.config/gitlab-contribution-tracker"
if [ -d "$CONFIG_DIR" ]; then
    read -p "  Do you also want to delete configuration files? (y/N): " answer
    if [[ "$answer" =~ ^[yY]$ ]]; then
        rm -rf "$CONFIG_DIR"
        echo "  Configuration deleted."
    else
        echo "  Configuration preserved: $CONFIG_DIR"
    fi
else
    echo "  No configuration files found."
fi

echo ""
echo "=== Uninstall complete! ==="
