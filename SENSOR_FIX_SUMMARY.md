# AirIQ Sensor Configuration Fix - Summary

## Date: March 29, 2026

### Problem Identified
The PM2.5 (PMS5003) sensor was not responding because all Python files referenced the wrong serial port.

### Root Cause
- **Incorrect port**: `/dev/ttyAMA10` (does not exist on Raspberry Pi 5)
- **Correct port**: `/dev/ttyAMA0` (default UART port for Pi 5)

### Files Updated

#### Serial Port Updates (PMS5003)
1. ✅ `pms5003_reader.py` - 3 references updated
2. ✅ `pms5003_test.py` - Line 11 updated  
3. ✅ `pm25_adafruit_test.py` - Updated
4. ✅ `test_sensors.py` - 4 references updated
5. ✅ `run_server.py` - Line 234 updated
6. ✅ `sensor_dashboard.py` - Line 67 updated
7. ✅ `pms5003_web_ui.py` - Line 48 updated
8. ✅ `combined_sensor_reader.py` - 2 references updated

#### Error Handling Improvements
1. ✅ `bme680_reader.py` - Added alternate I2C address fallback (0x77 → 0x76)
2. ✅ `ens160_reader.py` - Added alternate I2C address fallback (0x53 → 0x52)
3. ✅ `test_sensors.py` - Added diagnostic messages for troubleshooting

#### New Tools Created
1. ✅ `i2c_scanner.py` - Scans for connected I2C devices to diagnose sensor detection

### Results

**Before Fix:**
```
❌ PMS5003: No data received (timeout on /dev/ttyAMA10)
❌ BME680: Not tested
❌ ENS160: Not tested
```

**After Fix:**
```
✅ PMS5003: Connected and reading data
   - PM1.0: 3 µg/m³
   - PM2.5: 5 µg/m³
   - PM10:  6 µg/m³

❌ BME680: Not connected (hardware not present)
❌ ENS160: Not connected (hardware not present)
```

### Configuration Reference

| Sensor | Connection | Address/Port |
|--------|------------|---------------|
| PMS5003 | Serial UART | `/dev/ttyAMA0` @ 9600 baud |
| BME680 | I2C | `0x77` (default) or `0x76` (alternate) |
| ENS160 | I2C | `0x53` (default) or `0x52` (alternate) |

### Troubleshooting I2C Sensors

If BME680 or ENS160 aren't responding:

1. **Check I2C is enabled:**
   ```bash
   sudo raspi-config
   # Interface Options → I2C → Enable
   ```

2. **Scan for connected devices:**
   ```bash
   python3 i2c_scanner.py
   # or
   i2cdetect -y 1
   ```

3. **Verify wiring:**
   - SDA → GPIO 2 (Pin 3)
   - SCL → GPIO 3 (Pin 5)
   - 3.3V → Pin 1
   - GND → Pin 6

4. **Check power supply:**
   - Sensors need proper 3.3V
   - Check for loose connections

### Testing

Run comprehensive sensor test:
```bash
python3 test_sensors.py
```

Run with mock data (if sensors unavailable):
```bash
python3 run_server.py  # Falls back to NullSensor
```

---
**Status**: ✅ Complete - PM2.5 sensor fully operational
