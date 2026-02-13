"""SQLite database for AirIQ sensor readings"""
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'airiq.db')

def init_db():
    """Initialize database with readings table for all sensors"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check if table exists and has all required columns
    c.execute("PRAGMA table_info(readings)")
    columns = {row[1] for row in c.fetchall()}
    
    # If old table exists, drop it and create new one
    if 'temperature' not in columns and columns:
        c.execute('DROP TABLE IF EXISTS readings')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            pm1 REAL,
            pm25 REAL,
            pm10 REAL,
            temperature REAL,
            humidity REAL,
            pressure REAL,
            gas REAL,
            altitude REAL,
            aqi INTEGER,
            tvoc REAL,
            eco2 REAL
        )
    ''')
    conn.commit()
    conn.close()

def insert_reading(pm1=None, pm25=None, pm10=None, temperature=None, humidity=None, 
                   pressure=None, gas=None, altitude=None, aqi=None, tvoc=None, eco2=None):
    """Insert a new sensor reading with all sensor data"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO readings 
                 (timestamp, pm1, pm25, pm10, temperature, humidity, pressure, gas, altitude, aqi, tvoc, eco2) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (datetime.now(), pm1, pm25, pm10, temperature, humidity, pressure, gas, altitude, aqi, tvoc, eco2))
    conn.commit()
    conn.close()

def get_latest_reading():
    """Get the most recent sensor reading with all data"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT pm1, pm25, pm10, temperature, humidity, pressure, gas, altitude, aqi, tvoc, eco2, timestamp 
                 FROM readings ORDER BY timestamp DESC LIMIT 1''')
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'pm1': row[0], 'pm25': row[1], 'pm10': row[2],
            'temperature': row[3], 'humidity': row[4], 'pressure': row[5],
            'gas': row[6], 'altitude': row[7], 'aqi': row[8], 'tvoc': row[9],
            'eco2': row[10], 'timestamp': row[11]
        }
    return None

def get_history_24h():
    """Get last 24 hours of readings with all data points"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get all data from last 24 hours
    c.execute('''
        SELECT 
            strftime('%H:%M', timestamp) as time,
            pm1, pm25, pm10, temperature, humidity, pressure, gas, altitude, aqi, tvoc, eco2
        FROM readings
        WHERE timestamp > datetime('now', '-24 hours')
        ORDER BY timestamp
    ''')
    
    rows = c.fetchall()
    conn.close()
    
    history = [{
        'time': row[0], 'pm1': row[1], 'pm25': row[2], 'pm10': row[3],
        'temperature': row[4], 'humidity': row[5], 'pressure': row[6],
        'gas': row[7], 'altitude': row[8], 'aqi': row[9], 'tvoc': row[10], 'eco2': row[11]
    } for row in rows]
    
    # If no data, return placeholder with current time
    if not history:
        now = datetime.now()
        history = [{'time': (now - timedelta(hours=i)).strftime('%H:%M'), 'pm1': 0, 'pm25': 0, 'pm10': 0,
                   'temperature': 0, 'humidity': 0, 'pressure': 0, 'gas': 0, 'altitude': 0, 'aqi': 0, 'tvoc': 0, 'eco2': 0} 
                   for i in range(24)][::-1]
    
    return history
    
    # If no data, return placeholder with current time
    if not history:
        now = datetime.now()
        history = [{'time': (now - timedelta(hours=i)).strftime('%H:%M'), 'pm25': 0, 'pm10': 0} 
                   for i in range(24)][::-1]
    
    return history

def get_all_records():
    """Get all sensor readings from database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT timestamp, pm1, pm25, pm10, temperature, humidity, pressure, gas, altitude, aqi, tvoc, eco2 
                 FROM readings ORDER BY timestamp DESC''')
    rows = c.fetchall()
    conn.close()
    
    records = [{
        'timestamp': row[0], 'pm1': row[1], 'pm25': row[2], 'pm10': row[3],
        'temperature': row[4], 'humidity': row[5], 'pressure': row[6],
        'gas': row[7], 'altitude': row[8], 'aqi': row[9], 'tvoc': row[10], 'eco2': row[11]
    } for row in rows]
    return records

def clear_old_data(days=30):
    """Remove readings older than specified days"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM readings WHERE timestamp < datetime("now", "-" || ? || " days")',
              (days,))
    conn.commit()
    conn.close()

# Initialize on import
init_db()
