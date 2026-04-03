#!/usr/bin/env python3
"""
PMS5003 Air Quality Monitor with Web UI
Displays real-time PM sensor data in a web browser
"""

from flask import Flask, render_template, jsonify, send_from_directory
from pms5003_reader import PMS5003
import threading
import time
import os

app = Flask(__name__)

# Global variables to store sensor data
sensor_data = {
    'pm1_atm': 0,
    'pm25_atm': 0,
    'pm10_atm': 0,
    'timestamp': '',
    'connected': False,
    'error': None
}

# Sensor instance
sensor = None
sensor_lock = threading.Lock()

def get_air_quality_level(pm25):
    """Get air quality level based on PM2.5"""
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
    global sensor_data, sensor
    
    sensor = PMS5003(port='/dev/ttyAMA0', baudrate=9600)
    
    if not sensor.connect():
        with sensor_lock:
            sensor_data['connected'] = False
            sensor_data['error'] = 'Failed to connect to sensor'
        return
    
    with sensor_lock:
        sensor_data['connected'] = True
        sensor_data['error'] = None
    
    print("Sensor connected, starting data collection...")
    
    while True:
        try:
            data = sensor.read_data()
            
            if data:
                with sensor_lock:
                    sensor_data.update({
                        'pm1_atm': data['pm1_atm'],
                        'pm25_atm': data['pm25_atm'],
                        'pm10_atm': data['pm10_atm'],
                        'timestamp': data['timestamp'],
                        'connected': True,
                        'error': None
                    })
                print(f"Read data: PM2.5={data['pm25_atm']} PM10={data['pm10_atm']} PM1={data['pm1_atm']}")
            else:
                print("No data received from sensor")
                with sensor_lock:
                    sensor_data['error'] = 'Failed to read data'
            
            time.sleep(2)  # Read every 2 seconds
            
        except Exception as e:
            with sensor_lock:
                sensor_data['error'] = str(e)
                sensor_data['connected'] = False
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
    
    # Add air quality level
    aqi = get_air_quality_level(data['pm25_atm'])
    data['aqi'] = aqi
    
    return jsonify(data)

@app.route('/api/status')
def get_status():
    """API endpoint to get sensor status"""
    with sensor_lock:
        return jsonify({
            'connected': sensor_data['connected'],
            'error': sensor_data['error']
        })

@app.route('/api/history')
def get_history():
    """API endpoint to get current and historical data"""
    with sensor_lock:
        current_data = sensor_data.copy()
    
    # Add air quality level
    aqi = get_air_quality_level(current_data['pm25_atm'])
    
    # Format current data for frontend
    current = {
        'pm1': current_data['pm1_atm'],
        'pm25': current_data['pm25_atm'],
        'pm10': current_data['pm10_atm'],
        'timestamp': current_data['timestamp'],
        'aqi': aqi['level'],
        'aqi_color': aqi['color'],
        'aqi_description': aqi['description']
    }
    
    # For now, create a simple history from current reading
    # In future, this could pull from database
    history = []
    if current_data['timestamp']:
        history.append({
            'time': current_data['timestamp'],
            'pm25': current_data['pm25_atm'],
            'pm10': current_data['pm10_atm']
        })
    
    return jsonify({
        'current': current,
        'history': history,
        'error': current_data.get('error')
    })

@app.route('/api/db/all')
def get_all_data():
    """API endpoint to get all database records (placeholder)"""
    # Return empty array for now since we don't have database storage in this version
    return jsonify([])

@app.route('/logo/<filename>')
def serve_logo(filename):
    """Serve logo files"""
    return send_from_directory('logo', filename)

if __name__ == '__main__':
    # Start sensor reading in background thread
    sensor_thread = threading.Thread(target=read_sensor_loop, daemon=True)
    sensor_thread.start()
    
    print("Starting web server on http://0.0.0.0:5000")
    print("Open your browser and navigate to http://<raspberry-pi-ip>:5000")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
