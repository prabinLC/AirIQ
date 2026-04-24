# AirIQ Kiosk Mode Setup

This guide sets up the AirIQ dashboard to run in kiosk mode automatically on boot.

## Prerequisites

Ensure these packages are installed on your Raspberry Pi:

```bash
sudo apt-get update
sudo apt-get install -y chromium-browser curl
```

## Installation

### Option 1: Using systemd (Recommended)

1. Make the kiosk script executable:
```bash
chmod +x /home/airiq/Desktop/finalProject/AirIQ/airiq-kiosk.sh
```

2. Install the systemd services:
```bash
# System-wide service (requires sudo)
sudo cp /home/airiq/Desktop/finalProject/AirIQ/airiq-server.service /etc/systemd/system/
sudo cp /home/airiq/Desktop/finalProject/AirIQ/airiq-kiosk.service /etc/systemd/user/

# Or for user services only (no sudo):
mkdir -p ~/.config/systemd/user/
cp /home/airiq/Desktop/finalProject/AirIQ/airiq-server.service ~/.config/systemd/user/
cp /home/airiq/Desktop/finalProject/AirIQ/airiq-kiosk.service ~/.config/systemd/user/
```

3. Reload systemd and enable services:
```bash
# If using system services:
sudo systemctl daemon-reload
sudo systemctl enable airiq-server
sudo systemctl start airiq-server

# If using user services:
systemctl --user daemon-reload
systemctl --user enable airiq-server
systemctl --user enable airiq-kiosk
systemctl --user start airiq-server
systemctl --user start airiq-kiosk
```

4. Check service status:
```bash
systemctl --user status airiq-server
systemctl --user status airiq-kiosk
```

### Option 2: Using Desktop Autostart (Alternative)

1. Make scripts executable:
```bash
chmod +x /home/airiq/Desktop/finalProject/AirIQ/airiq-kiosk.sh
```

2. Copy desktop entry to autostart:
```bash
mkdir -p ~/.config/autostart/
cp /home/airiq/Desktop/finalProject/AirIQ/airiq-kiosk.desktop ~/.config/autostart/
```

The dashboard will start automatically when you log in to the desktop.

## Verify Setup

1. Reboot to test:
```bash
sudo reboot
```

2. Check logs (systemd):
```bash
journalctl --user -u airiq-server -f
journalctl --user -u airiq-kiosk -f
```

3. Or check if server is running:
```bash
curl http://localhost:8000
```

## Manual Start/Stop

If using systemd:
```bash
# Start
systemctl --user start airiq-server
systemctl --user start airiq-kiosk

# Stop
systemctl --user stop airiq-kiosk
systemctl --user stop airiq-server

# Restart
systemctl --user restart airiq-server
```

## Exit Kiosk Mode

To exit fullscreen kiosk mode:
- Press `Alt+F4` (traditional exit)
- Or configure a keyboard shortcut if needed

## Troubleshooting

### Server won't start
```bash
cd /home/airiq/Desktop/finalProject/AirIQ
python3 run_server.py
```

### Browser won't launch
- Check if Chromium is installed: `which chromium-browser`
- Check display: `echo $DISPLAY` (should be `:0`)
- Test browser launch manually: `chromium-browser --kiosk http://localhost:8000`

### Permissions issues
- Ensure the airiq user owns the scripts: `sudo chown airiq:airiq /home/airiq/Desktop/finalProject/AirIQ/airiq-*`
- Make scripts executable: `chmod +x /home/airiq/Desktop/finalProject/AirIQ/airiq-*.sh`

## Logs

View system logs:
```bash
# Journalctl (systemd)
journalctl -u airiq-server -f
journalctl -u airiq-kiosk -f

# Or check startup log
tail -f ~/.local/share/systemd/user-journal.log
```
