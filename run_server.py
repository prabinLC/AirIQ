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

from db import insert_reading, get_history_24h, get_all_records
from pms5003_reader import PMS5003
from bme680_reader import BME680Reader
from ens160_reader import ENS160Reader

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(ROOT, 'templates')

# Shared latest sensor data, updated by background thread
_latest_data = {'starting': True}  # Initialize with loading state
_data_lock = threading.Lock()


def sensor_loop(pms, bme, ens):
    """Background thread: reads all sensors in parallel every 2 seconds and saves to DB."""
    # Track which sensors are mocks (not real hardware)
    pms_is_mock = getattr(pms, 'is_mock', False)
    bme_is_mock = getattr(bme, 'is_mock', False)
    ens_is_mock = getattr(ens, 'is_mock', False)
    
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

            if ens_data:
                for k in ('aqi', 'aqi_description', 'tvoc', 'eco2'):
                    flat[k] = ens_data[k]

            # Track sensor status: ONLY real sensors count as active
            flat['pms_active'] = pms_data is not None and not pms_is_mock
            flat['bme_active'] = bme_data is not None and not bme_is_mock
            flat['ens_active'] = ens_data is not None and not ens_is_mock

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

        # API: current + 24h history
        if p == '/api/history':
            with _data_lock:
                current = dict(_latest_data)
            history = get_history_24h()
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
    is_mock = True  # Mark as unavailable, not real hardware
    
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
    """Connect sensors, start background reader, then serve."""
    print("Connecting to sensors...")

    try:
        import board, busio
        shared_i2c = busio.I2C(board.SCL, board.SDA)
    except (ImportError, RuntimeError):
        print("Could not initialize I2C bus, using mock mode")
        shared_i2c = None

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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run(port)
