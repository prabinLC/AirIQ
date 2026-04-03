# AirIQ - Real-Time Air Quality Monitor

A production-ready web dashboard for real-time air quality monitoring using three integrated sensors on Raspberry Pi 5.

## Features

✅ **Three Real Sensors**
- **PMS5003**: Particulate matter (PM1.0, PM2.5, PM10)
- **BME680**: Environmental data (temperature, humidity, pressure, gas)
- **ENS160**: Air quality index (AQI, eCO2, TVOC)

✅ **Real-time Dashboard**
- Live metrics for all 12 sensor values
- Interactive 24-hour history chart
- Sensor connection status indicators
- EPA/WHO air quality scales
- Responsive design with professional UI

✅ **Data Persistence**
- SQLite database stores all readings
- Automatic 24-hour history retention
- RESTful API endpoints for data access

✅ **Optimized Performance**
- Parallel sensor reads (3 sensors simultaneously)
- 2-second polling interval
- CORS enabled for cross-origin requests

## Hardware Requirements

- **Raspberry Pi 5** (BCM2712)
- **PMS5003**: Connected to UART (/dev/ttyAMA0 @ 9600 baud)
- **BME680**: I2C address 0x77 (fallback: 0x76)
- **ENS160**: I2C address 0x53 (fallback: 0x52)

## Project Structure

```
AirIQ/
├── run_server.py              # HTTP server with sensor thread
├── pms5003_reader.py          # PMS5003 UART reader
├── bme680_reader.py           # BME680 I2C reader
├── ens160_reader.py           # ENS160 I2C reader
├── combined_sensor_reader.py  # Unified sensor interface
├── db.py                      # SQLite database manager
├── templates/
│   └── index.html             # Dashboard UI
├── static/                    # Static assets
├── logo/                      # Logo images
└── README.md                  # This file
```

## Quick Start

### 1. Installation

```bash
cd /home/airiq/Desktop/finalProject/AirIQ

# Install dependencies
pip3 install pyserial adafruit-circuitpython-bme680 adafruit-circuitpython-ens160

# Start the server
python3 run_server.py
```

### 2. Access Dashboard

Open browser and navigate to: **http://localhost:8000**

### 3. API Endpoints

```bash
# Current sensor readings
curl http://localhost:8000/api/data

# 24-hour history
curl http://localhost:8000/api/history

# Sensor connection status
curl http://localhost:8000/api/sensor/status

# All database records
curl http://localhost:8000/api/db/all
```

## Sensor Configuration

### PMS5003 (UART)
- Port: `/dev/ttyAMA0`
- Baudrate: 9600
- Protocol: Binary with 0x42 0x4D magic bytes
- Data: PM1.0, PM2.5, PM10 (both CF and ATM modes)

### BME680 (I2C)
- Primary Address: 0x77
- Fallback Address: 0x76
- Readings: Temperature, Humidity, Pressure, Gas Resistance, Altitude

### ENS160 (I2C)
- Primary Address: 0x53
- Fallback Address: 0x52
- Readings: AQI, AQI Description, TVOC, eCO2

## API Response Format

```json
{
  "connected": true,
  "timestamp": "2026-04-03 01:41:58",
  "pm1": 22,
  "pm25": 32,
  "pm10": 37,
  "temperature": 32.8,
  "humidity": 36.87,
  "pressure": 994.21,
  "gas": 52651,
  "altitude": 159.75,
  "aqi": 2,
  "aqi_description": "Good",
  "tvoc": 129,
  "eco2": 596,
  "pms_active": true,
  "bme_active": true,
  "ens_active": true
}
```

## Air Quality Scales

### PM2.5 Levels (EPA)
- **Good** (0-12.0): Green
- **Moderate** (12.1-35.4): Yellow
- **Unhealthy for Sensitive Groups** (35.5-55.4): Orange
- **Unhealthy** (55.5-150.4): Red
- **Very Unhealthy** (150.5-250.4): Purple
- **Hazardous** (>250.5): Maroon

### AQI Levels
- **0-50**: Good (Green)
- **51-100**: Moderate (Yellow)
- **101-150**: Unhealthy for Sensitive Groups (Orange)
- **151-200**: Unhealthy (Red)
- **201-300**: Very Unhealthy (Purple)
- **301+**: Hazardous (Maroon)

## Troubleshooting

### Sensor Not Connecting
```bash
# Check I2C devices
python3 i2c_scanner.py

# Test PMS5003 serial
python3 test_sensors.py

# View verbose connection status
curl http://localhost:8000/api/sensor/status | python3 -m json.tool
```

### Port Already in Use
```bash
# Kill existing server
pkill -f "python3 run_server.py"

# Start fresh
python3 run_server.py
```

### Permission Errors
```bash
# Ensure user in dialout group for serial access
sudo usermod -a -G dialout $USER
newgrp dialout

# Restart server
python3 run_server.py
```

## Performance

- **Sensor Read Time**: ~4s total (3 sensors in parallel, 2s interval)
- **Data Point Frequency**: Every 2 seconds
- **Dashboard Refresh**: Every 10 seconds
- **Database Query**: O(1) for latest, O(n) for 24h history

## Pi 5 UART Configuration

This project requires specific device tree overlay for Raspberry Pi 5:

```
# /boot/firmware/config.txt
dtoverlay=uart0-pi5
```

## Building from Source

```bash
# Clone repository
git clone https://github.com/prabinLC/AirIQ.git
cd AirIQ

# Install dependencies
pip3 install -r requirements.txt

# Run server
python3 run_server.py 8000
```

## Development

### Adding New Sensors

1. Create reader file: `newsensor_reader.py`
2. Implement `connect()` and `read_data()` methods
3. Add to `combined_sensor_reader.py`
4. Update dashboard UI in `templates/index.html`

### Database Schema

```sql
CREATE TABLE readings (
  id INTEGER PRIMARY KEY,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  pm1 REAL, pm25 REAL, pm10 REAL,
  temperature REAL, humidity REAL, pressure REAL,
  gas REAL, altitude REAL,
  aqi INTEGER, tvoc REAL, eco2 REAL
);
```

## License & Credits

Senior Design Project - AirIQ Team
Raspberry Pi 5 | Adafruit Sensors | Flask Server
