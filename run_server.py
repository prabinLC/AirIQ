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
_latest_data = {}
_data_lock = threading.Lock()


def sensor_loop(pms, bme, ens):
    """Background thread: reads all sensors every 2 seconds and saves to DB."""
    while True:
        try:
            pms_data = pms.read_data()
            bme_data = bme.read_data()
            ens_data = ens.read_data()

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

            # Save to database
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

        local = os.path.join(ROOT, p.lstrip('/'))
        if os.path.exists(local) and os.path.isfile(local):
            return self.serve_file(local)

        self.send_error(404, 'Not Found')

    def log_message(self, format, *args):
        pass


def run(port=8000):
    """Connect sensors, start background reader, then serve."""
    print("Connecting to sensors...")

    import board, busio
    shared_i2c = busio.I2C(board.SCL, board.SDA)

    pms = PMS5003(port='/dev/ttyS0', baudrate=9600)
    bme = BME680Reader(i2c_address=0x77)
    ens = ENS160Reader(i2c_address=0x53)

    pms_ok = pms.connect()
    print(f"{'✓' if pms_ok else '✗'} PMS5003 (particulate matter)")

    bme_ok = bme.connect(shared_i2c=shared_i2c)
    print(f"{'✓' if bme_ok else '✗'} BME680  (temperature / humidity / pressure / gas)")

    ens_ok = ens.connect(shared_i2c=shared_i2c)
    print(f"{'✓' if ens_ok else '✗'} ENS160  (AQI / TVOC / eCO2)")

    if not any([pms_ok, bme_ok, ens_ok]):
        print("No sensors connected. Aborting.")
        sys.exit(1)

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
