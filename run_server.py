#!/usr/bin/env python3
"""
AirIQ Sensor Dashboard Server
Real-time air quality monitoring using PMS5003, BME680, and ENS160 sensors.

"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import os
import urllib.parse
import time
import mimetypes
import sys
import threading
from datetime import datetime

from db import insert_reading, get_history_24h, get_history_30m, get_all_records, cleanup_old_records
from pms5003_reader import PMS5003
from bme680_reader import BME680Reader
from ens160_reader import ENS160Reader

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(ROOT, 'templates')

# Shared latest sensor data, updated by background thread
_latest_data = {'starting': True}  # Initialize with loading state
_data_lock = threading.Lock()


def calculate_epa_aqi(pm25):
    """Calculate EPA AQI from PM2.5 reading"""
    if pm25 is None:
        return None
    
    # EPA AQI breakpoints for PM2.5 (µg/m³)
    # AQI formula: ((IHi - ILo) / (BPhi - BPlo)) * (Cp - BPlo) + ILo
    breakpoints = [
        (0, 12.0, 0, 50),           # Good
        (12.1, 35.4, 51, 100),      # Moderate
        (35.5, 55.4, 101, 150),     # Unhealthy for Sensitive Groups
        (55.5, 150.4, 151, 200),    # Unhealthy
        (150.5, 250.4, 201, 300),   # Very Unhealthy
        (250.5, float('inf'), 301, 500),  # Hazardous
    ]
    
    for bp_lo, bp_hi, aqi_lo, aqi_hi in breakpoints:
        if bp_lo <= pm25 <= bp_hi:
            aqi = ((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (pm25 - bp_lo) + aqi_lo
            return round(aqi)
    
    return 0


def get_aqi_description(aqi_value):
    """Get human-readable AQI category from EPA AQI value"""
    if aqi_value is None or aqi_value < 0:
        return 'Unknown'
    if aqi_value <= 50:
        return 'Good'
    if aqi_value <= 100:
        return 'Moderate'
    if aqi_value <= 150:
        return 'Unhealthy for Sensitive Groups'
    if aqi_value <= 200:
        return 'Unhealthy'
    if aqi_value <= 300:
        return 'Very Unhealthy'
    return 'Hazardous'


def sensor_loop(pms, bme, ens):
    """Background thread: reads all sensors in parallel every 2 seconds and saves to DB."""
    
    while True:
        try:
            # Read all sensors in parallel using threads
            results = {}
            
            def read_pms():
                results['pms'] = pms.read_data()
            
            def read_bme():
                results['bme'] = bme.read_data()
            
            def read_ens():
                results['ens'] = ens.read_data()
            
            threads = [
                threading.Thread(target=read_pms),
                threading.Thread(target=read_bme),
                threading.Thread(target=read_ens)
            ]
            
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            pms_data = results.get('pms')
            bme_data = results.get('bme')
            ens_data = results.get('ens')

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            flat = {'timestamp': now}

            if pms_data:
                flat['pm1']  = pms_data['pm1_atm']
                flat['pm25'] = pms_data['pm25_atm']
                flat['pm10'] = pms_data['pm10_atm']

            if bme_data:
                for k in ('temperature', 'humidity', 'pressure', 'gas', 'altitude'):
                    flat[k] = bme_data[k]

            # Calculate EPA AQI from PM2.5 (instead of using raw ENS160 AQI)
            if pms_data:
                epa_aqi = calculate_epa_aqi(pms_data['pm25_atm'])
                flat['aqi'] = epa_aqi
                flat['aqi_description'] = get_aqi_description(epa_aqi)
            elif ens_data:
                # Fallback to ENS160 AQI if no PM2.5 data
                flat['aqi'] = ens_data.get('aqi')
                flat['aqi_description'] = ens_data.get('aqi_description', 'Unknown')
            
            # Store original ENS160 data if available (for reference)
            if ens_data:
                flat['ens160_aqi'] = ens_data.get('aqi')
                flat['tvoc'] = ens_data.get('tvoc')
                flat['eco2'] = ens_data.get('eco2')
            else:
                flat['tvoc'] = 0
                flat['eco2'] = 0

            # Track sensor status: mark as active if data is available
            flat['pms_active'] = pms_data is not None
            flat['bme_active'] = bme_data is not None
            flat['ens_active'] = ens_data is not None

            # Only save to DB if at least one sensor has data
            if any([pms_data, bme_data, ens_data]):
                insert_reading(
                    pm1=flat.get('pm1'),
                    pm25=flat.get('pm25'),
                    pm10=flat.get('pm10'),
                    temperature=flat.get('temperature'),
                    humidity=flat.get('humidity'),
                    pressure=flat.get('pressure'),
                    gas=flat.get('gas'),
                    altitude=flat.get('altitude'),
                    aqi=flat.get('aqi'),
                    tvoc=flat.get('tvoc'),
                    eco2=flat.get('eco2'),
                )

            with _data_lock:
                _latest_data.clear()
                _latest_data.update(flat)
                _latest_data.pop('starting', None)  # Remove loading flag once we have data

            print(
                f"[{now}] "
                f"PM1={flat.get('pm1','?')} PM2.5={flat.get('pm25','?')} PM10={flat.get('pm10','?')} | "
                f"Temp={flat.get('temperature','?')}°C Hum={flat.get('humidity','?')}% Pres={flat.get('pressure','?')}hPa | "
                f"AQI={flat.get('aqi','?')} TVOC={flat.get('tvoc','?')}ppb eCO2={flat.get('eco2','?')}ppm"
            )

        except Exception as e:
            print(f"[sensor_loop error] {e}")

        time.sleep(2)


def cleanup_loop():
    """Background thread: cleanup old database records once per day"""
    import time
    last_cleanup = 0
    while True:
        now = time.time()
        # Run cleanup once every 24 hours (86400 seconds)
        if now - last_cleanup >= 86400:
            try:
                deleted = cleanup_old_records(days=7)
                last_cleanup = now
            except Exception as e:
                print(f"[cleanup_loop error] {e}")
        
        time.sleep(3600)  # Check every hour


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the AirIQ dashboard."""

    def send_json(self, obj, status=200):
        data = json.dumps(obj).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)
    
    def send_error(self, code, message=None):
        """Override send_error to include CORS headers"""
        self.send_response(code)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        error_message = self.responses.get(code, ('Unknown',))[0]
        self.wfile.write(f"<html><body><h1>{code} {error_message}</h1></body></html>".encode('utf-8'))

    def serve_file(self, fullpath):
        if not os.path.exists(fullpath) or not os.path.isfile(fullpath):
            self.send_error(404)
            return
        ctype = mimetypes.guess_type(fullpath)[0] or 'application/octet-stream'
        with open(fullpath, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        p = parsed.path

        if p in ('/', '/index.html'):
            return self.serve_file(os.path.join(TEMPLATES, 'index.html'))

        if p.startswith('/static/') or p.startswith('/logo/'):
            return self.serve_file(os.path.join(ROOT, p.lstrip('/')))

        # API: current reading
        if p == '/api/data':
            with _data_lock:
                current = dict(_latest_data)
            return self.send_json({'connected': bool(current), **current})

        # API: current + 30 minute history
        if p == '/api/history':
            with _data_lock:
                current = dict(_latest_data)
            history = get_history_30m()
            return self.send_json({'current': current, 'history': history})

        # API: all DB records
        if p == '/api/db/all':
            return self.send_json({'records': get_all_records()})

        # API: sensor status
        if p == '/api/sensor/status':
            with _data_lock:
                current = dict(_latest_data)
            return self.send_json({
                'pms5003': current.get('pms_active', False),
                'bme680': current.get('bme_active', False),
                'ens160': current.get('ens_active', False),
            })

        local = os.path.join(ROOT, p.lstrip('/'))
        if os.path.exists(local) and os.path.isfile(local):
            return self.serve_file(local)

        self.send_error(404, 'Not Found')

    def log_message(self, format, *args):
        pass





class NullSensor:
    """Sensor that returns no data (disconnected/unavailable)."""
    
    def __init__(self, sensor_type='null'):
        self.sensor_type = sensor_type
    
    def connect(self, shared_i2c=None):
        return True
    
    def disconnect(self):
        pass
    
    def read_data(self):
        """Always returns None - no data available."""
        return None


def run(port=8000):
    """Connect sensors, start background reader, then serve.
    
    Args:
        port: HTTP port to serve on
    """
    print("Connecting to sensors...")
    
    # Try to initialize I2C bus for I2C sensors
    shared_i2c = None
    try:
        import board, busio
        shared_i2c = busio.I2C(board.SCL, board.SDA)
    except (ImportError, RuntimeError) as e:
        print(f"⚠ Could not initialize I2C bus: {e}")
        print("  → I2C sensors will be unavailable (BME680, ENS160)")
        shared_i2c = None

    # Initialize sensors
    pms = PMS5003(port='/dev/ttyAMA0', baudrate=9600)
    bme = BME680Reader(i2c_address=0x77)
    ens = ENS160Reader(i2c_address=0x53)

    pms_ok = pms.connect()
    if not pms_ok:
        pms = NullSensor('pms')
    print(f"{'✓' if pms_ok else '✗'} PMS5003 (particulate matter)")

    bme_ok = bme.connect(shared_i2c=shared_i2c)
    if not bme_ok:
        bme = NullSensor('bme')
    print(f"{'✓' if bme_ok else '✗'} BME680  (temperature / humidity / pressure / gas)")

    ens_ok = ens.connect(shared_i2c=shared_i2c)
    if not ens_ok:
        ens = NullSensor('ens')
    print(f"{'✓' if ens_ok else '✗'} ENS160  (AQI / TVOC / eCO2)")

    # Start background sensor-reading thread
    t = threading.Thread(target=sensor_loop, args=(pms, bme, ens), daemon=True)
    t.start()
    print("\n✓ Sensor loop started (reading every 2 s)")
    
    # Start background database cleanup thread (removes records older than 7 days)
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    print("✓ Database cleanup started (removes records older than 7 days)")

    server = ThreadingHTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f"✓ AirIQ Dashboard running at http://localhost:{port}")
    print(f"✓ Press Ctrl-C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n✓ Server stopped')
        server.shutdown()
        pms.disconnect()
        bme.disconnect()
        ens.disconnect()


if __name__ == '__main__':
    port = 8000
    
    # Parse command line arguments
    for arg in sys.argv[1:]:
        if arg.isdigit():
            port = int(arg)
        elif arg in ('--help', '-h'):
            print("Usage: python3 run_server.py [OPTIONS] [PORT]")
            print("  [PORT]           HTTP port (default: 8000)")
            print("  -h, --help       Show this help message")
            sys.exit(0)
    
    run(port)
