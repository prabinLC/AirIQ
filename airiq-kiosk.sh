#!/bin/bash
# AirIQ Kiosk Mode Launcher
# Launches the AirIQ dashboard in fullscreen kiosk mode

# Wait for server to start
echo "Waiting for AirIQ server to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000 > /dev/null 2>&1; then
        echo "Server is ready!"
        break
    fi
    sleep 1
done

# Get display device
export DISPLAY=:0

# Kill any existing Chromium processes
pkill -f "chromium|google-chrome" 2>/dev/null || true

# Wait a moment for cleanup
sleep 1

# Launch Chromium in fullscreen kiosk mode
chromium \
  --noerrdialogs \
  --disable-infobars \
  --disable-extensions \
  --disable-sync \
  --disable-translate \
  --no-first-run \
  --no-default-browser-check \
  --disable-popup-blocking \
  --disable-prompt-on-repost \
  --disable-background-networking \
  --disable-default-apps \
  --disable-preconnect \
  --disable-component-extensions-with-background-pages \
  --disable-breakpad \
  --disable-component-update \
  --disable-device-discovery-notifications \
  --disable-suggestions-ui \
  --disable-preconnect \
  --disable-sync-types=googleShoppingContent \
  --kiosk \
  --start-maximized \
  http://localhost:8000 &

# Keep script running
wait
