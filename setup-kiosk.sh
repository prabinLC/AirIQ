#!/bin/bash
# AirIQ Kiosk Mode Automated Setup
# Run this script to set up kiosk mode automatically

set -e  # Exit on any error

echo "╔════════════════════════════════════════════════════════╗"
echo "║      AirIQ Kiosk Mode - Automated Setup               ║"
echo "╚════════════════════════════════════════════════════════╝"

PROJECT_DIR="/home/airiq/Desktop/finalProject/AirIQ"
CURRENT_USER="${SUDO_USER:-$USER}"

# Check if running from correct directory
if [ ! -f "$PROJECT_DIR/run_server.py" ]; then
    echo "❌ Error: run_server.py not found in $PROJECT_DIR"
    exit 1
fi

echo ""
echo "📦 Installing dependencies..."
sudo apt-get update
sudo apt-get install -y chromium-browser curl 2>/dev/null || \
sudo apt-get install -y chromium-browser curl || \
    echo "⚠️  Could not install all dependencies, continuing anyway..."

echo ""
echo "📝 Setting up kiosk launcher script..."
chmod +x "$PROJECT_DIR/airiq-kiosk.sh"
echo "✓ Made airiq-kiosk.sh executable"

echo ""
echo "🔧 Setting up systemd services..."

# Create systemd user directory
mkdir -p "$HOME/.config/systemd/user/"

# Copy service files
cp "$PROJECT_DIR/airiq-server.service" "$HOME/.config/systemd/user/"
cp "$PROJECT_DIR/airiq-kiosk.service" "$HOME/.config/systemd/user/"
echo "✓ Copied service files to ~/.config/systemd/user/"

# Reload systemd
systemctl --user daemon-reload
echo "✓ Reloaded systemd daemon"

# Enable services
systemctl --user enable airiq-server
systemctl --user enable airiq-kiosk
echo "✓ Enabled services to start on boot"

echo ""
echo "🎯 Setup Complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Services installed:"
echo "  • airiq-server.service (Python backend)"
echo "  • airiq-kiosk.service (Browser kiosk display)"
echo ""
echo "Start services immediately:"
echo "  systemctl --user start airiq-server"
echo "  systemctl --user start airiq-kiosk"
echo ""
echo "Check status:"
echo "  systemctl --user status airiq-server"
echo "  systemctl --user status airiq-kiosk"
echo ""
echo "View logs:"
echo "  journalctl --user -u airiq-server -f"
echo "  journalctl --user -u airiq-kiosk -f"
echo ""
echo "To start on next boot:"
echo "  sudo reboot"
echo ""
echo "Exit kiosk mode: Press Alt+F4"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
