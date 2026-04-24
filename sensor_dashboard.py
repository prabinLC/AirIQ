#!/usr/bin/env python3
"""
Combined Air Quality Monitor with Web UI
Displays real-time data from all sensors (PMS5003, BME680, ENS160) in a web browser
"""

from flask import Flask, render_template, jsonify, send_from_directory
from pms5003_reader import PMS5003
from bme680_reader import BME680Reader
from ens160_reader import ENS160Reader
from db import insert_reading, get_latest_reading, get_history_24h, get_all_records
import threading
import time
import os

app = Flask(__name__)

# Global variables to store sensor data
sensor_data = {
    # PMS5003
    'pm1_atm': 0,
    'pm25_atm': 0,
    'pm10_atm': 0,
    # BME680
    'temperature': 0,
    'humidity': 0,
    'pressure': 0,
    'gas': 0,
    'altitude': 0,
    # ENS160
    'aqi': 0,
    'aqi_description': 'Unknown',
    'tvoc': 0,
    'eco2': 0,
    # Status
    'timestamp': '',
    'connected_sensors': {},
    'error': None
}

# Sensor instances
pms5003 = None
bme680 = None
ens160 = None
sensor_lock = threading.Lock()

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

def get_air_quality_level(pm25):
    """Get air quality level based on PM2.5"""
    if pm25 is None:
        pm25 = 0
    
    if pm25 <= 12:
        return {'level': 'Good', 'color': '#00e400', 'description': 'Air quality is satisfactory'}
    elif pm25 <= 35:
        return {'level': 'Moderate', 'color': '#ffff00', 'description': 'Air quality is acceptable'}
    elif pm25 <= 55:
        return {'level': 'Unhealthy for Sensitive Groups', 'color': '#ff7e00', 'description': 'Sensitive groups may experience health effects'}
    elif pm25 <= 150:
        return {'level': 'Unhealthy', 'color': '#ff0000', 'description': 'Everyone may begin to experience health effects'}
    elif pm25 <= 250:
        return {'level': 'Very Unhealthy', 'color': '#8f3f97', 'description': 'Health alert: everyone may experience serious effects'}
    else:
        return {'level': 'Hazardous', 'color': '#7e0023', 'description': 'Health warnings of emergency conditions'}

def read_sensor_loop():
    """Background thread to continuously read sensor data"""
    global sensor_data, pms5003, bme680, ens160
    
    # Initialize PMS5003
    pms5003 = PMS5003(port='/dev/ttyAMA0', baudrate=9600)
    pms_connected = pms5003.connect()
    
    # Initialize BME680
    bme680 = BME680Reader(i2c_address=0x77, temperature_offset=0)
    bme_connected = bme680.connect()
    
    # Initialize ENS160
    ens160 = ENS160Reader(i2c_address=0x53)
    ens_connected = ens160.connect()
    
    with sensor_lock:
        sensor_data['connected_sensors'] = {
            'pms5003': pms_connected,
            'bme680': bme_connected,
            'ens160': ens_connected
        }
        sensor_data['error'] = None if any([pms_connected, bme_connected, ens_connected]) else 'Failed to connect to any sensor'
    
    if not any([pms_connected, bme_connected, ens_connected]):
        print("ERROR: Could not connect to any sensors!")
        return
    
    print("Sensors connected, starting data collection...")
    
    while True:
        try:
            pms_data = None
            bme_data = None
            ens_data = None
            
            # Read from each sensor
            if pms_connected:
                pms_data = pms5003.read_data()
            if bme_connected:
                bme_data = bme680.read_data()
            if ens_connected:
                ens_data = ens160.read_data()
            
            # Update sensor data
            with sensor_lock:
                if pms_data:
                    sensor_data['pm1_atm'] = pms_data.get('pm1_atm', 0)
                    sensor_data['pm25_atm'] = pms_data.get('pm25_atm', 0)
                    sensor_data['pm10_atm'] = pms_data.get('pm10_atm', 0)
                
                if bme_data:
                    sensor_data['temperature'] = bme_data.get('temperature', 0)
                    sensor_data['humidity'] = bme_data.get('humidity', 0)
                    sensor_data['pressure'] = bme_data.get('pressure', 0)
                    sensor_data['gas'] = bme_data.get('gas', 0)
                    sensor_data['altitude'] = bme_data.get('altitude', 0)
                
                if ens_data:
                    sensor_data['aqi'] = ens_data.get('aqi', 0)
                    sensor_data['aqi_description'] = ens_data.get('aqi_description', 'Unknown')
                    sensor_data['tvoc'] = ens_data.get('tvoc', 0)
                    sensor_data['eco2'] = ens_data.get('eco2', 0)
                
                sensor_data['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
                sensor_data['error'] = None
            
            # Save to database
            if pms_data or bme_data or ens_data:
                insert_reading(
                    pm1=pms_data.get('pm1_atm') if pms_data else None,
                    pm25=pms_data.get('pm25_atm') if pms_data else None,
                    pm10=pms_data.get('pm10_atm') if pms_data else None,
                    temperature=bme_data.get('temperature') if bme_data else None,
                    humidity=bme_data.get('humidity') if bme_data else None,
                    pressure=bme_data.get('pressure') if bme_data else None,
                    gas=bme_data.get('gas') if bme_data else None,
                    altitude=bme_data.get('altitude') if bme_data else None,
                    aqi=ens_data.get('aqi') if ens_data else None,
                    tvoc=ens_data.get('tvoc') if ens_data else None,
                    eco2=ens_data.get('eco2') if ens_data else None
                )
                print(f"✓ Data saved - PMS5003: {pms_data.get('pm25_atm') if pms_data else 'N/A'}, BME680: {bme_data.get('temperature') if bme_data else 'N/A'}°C, ENS160: {ens_data.get('aqi') if ens_data else 'N/A'}")
            
            time.sleep(2)  # Read every 2 seconds
            
        except Exception as e:
            with sensor_lock:
                sensor_data['error'] = str(e)
            print(f"Error during reading: {e}")
            time.sleep(5)

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    """API endpoint to get current sensor data"""
    with sensor_lock:
        data = sensor_data.copy()
    
    # Add air quality level based on PM2.5 (EPA AQI standard)
    aqi_level = get_air_quality_level(data['pm25_atm'])
    epa_aqi = calculate_epa_aqi(data['pm25_atm'])
    data['pm_aqi'] = aqi_level
    data['aqi'] = epa_aqi  # Override ENS160 AQI with EPA AQI based on PM2.5
    data['aqi_description'] = aqi_level['level']
    
    return jsonify(data)

@app.route('/api/status')
def get_status():
    """API endpoint to get sensor status"""
    with sensor_lock:
        return jsonify({
            'connected_sensors': sensor_data['connected_sensors'],
            'error': sensor_data['error']
        })

@app.route('/api/history')
def get_history():
    """API endpoint to get current and historical data"""
    with sensor_lock:
        current_data = sensor_data.copy()
    
    # Format current data for frontend
    pm_aqi = get_air_quality_level(current_data['pm25_atm'])
    epa_aqi = calculate_epa_aqi(current_data['pm25_atm'])
    current = {
        'pm1': round(current_data['pm1_atm'], 1),
        'pm25': round(current_data['pm25_atm'], 1),
        'pm10': round(current_data['pm10_atm'], 1),
        'temperature': round(current_data['temperature'], 1),
        'humidity': round(current_data['humidity'], 1),
        'pressure': round(current_data['pressure'], 1),
        'gas': round(current_data['gas'], 0),
        'altitude': round(current_data['altitude'], 1),
        'aqi': epa_aqi,  # Use calculated EPA AQI instead of ENS160 value
        'aqi_description': pm_aqi['level'],
        'tvoc': round(current_data['tvoc'], 1),
        'eco2': round(current_data['eco2'], 1),
        'timestamp': current_data['timestamp'],
        'pm_aqi': pm_aqi
    }
    
    # Get historical data
    history = get_history_24h()
    formatted_history = []
    for h in history:
        formatted_history.append({
            'time': h['time'],
            'pm1': h['pm1'],
            'pm25': h['pm25'],
            'pm10': h['pm10'],
            'temperature': h['temperature'],
            'humidity': h['humidity'],
            'pressure': h['pressure'],
            'tvoc': h['tvoc'],
            'eco2': h['eco2'],
            'aqi': h['aqi']
        })
    
    return jsonify({
        'current': current,
        'history': formatted_history,
        'error': current_data.get('error')
    })

@app.route('/api/db/all')
def get_all_data():
    """API endpoint to get all database records"""
    try:
        records = get_all_records()
        return jsonify({
            'records': records,
            'count': len(records)
        })
    except Exception as e:
        return jsonify({'error': str(e), 'records': []})

@app.route('/logo/<filename>')
def serve_logo(filename):
    """Serve logo files"""
    return send_from_directory('logo', filename)

if __name__ == '__main__':
    # Start sensor reading in background thread
    sensor_thread = threading.Thread(target=read_sensor_loop, daemon=True)
    sensor_thread.start()
    
    print("Starting web server on http://0.0.0.0:7002")
    print("Open your browser and navigate to http://<raspberry-pi-ip>:7002")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=7002, debug=False)
