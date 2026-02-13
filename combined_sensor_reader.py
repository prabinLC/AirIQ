#!/usr/bin/env python3
"""
Combined Sensor Reader - Reads all sensors simultaneously
Integrates PMS5003, BME680, and ENS160 sensor data
"""

import time
import threading
from pms5003_reader import PMS5003
from bme680_reader import BME680Reader
from ens160_reader import ENS160Reader
import db

class CombinedSensorReader:
    """Class to manage and read from all sensors"""
    
    def __init__(self, pms5003_port='/dev/ttyS0', bme680_address=0x77, ens160_address=0x53):
        """
        Initialize all sensors
        
        Args:
            pms5003_port: Serial port for PMS5003
            bme680_address: I2C address for BME680
            ens160_address: I2C address for ENS160
        """
        self.pms5003 = PMS5003(port=pms5003_port, baudrate=9600)
        self.bme680 = BME680Reader(i2c_address=bme680_address, temperature_offset=0)
        self.ens160 = ENS160Reader(i2c_address=ens160_address)
        
        self.pms5003_data = {}
        self.bme680_data = {}
        self.ens160_data = {}
        self.combined_data = {}
        self.data_lock = threading.Lock()
        
    def connect_all(self):
        """Connect to all sensors"""
        sensors_connected = 0
        
        print("Connecting to sensors...")
        
        if self.pms5003.connect():
            sensors_connected += 1
            print("✓ PMS5003 connected")
        else:
            print("✗ PMS5003 failed to connect")
        
        if self.bme680.connect():
            sensors_connected += 1
            print("✓ BME680 connected")
        else:
            print("✗ BME680 failed to connect")
        
        if self.ens160.connect():
            sensors_connected += 1
            print("✓ ENS160 connected")
        else:
            print("✗ ENS160 failed to connect")
        
        return sensors_connected > 0
    
    def disconnect_all(self):
        """Disconnect from all sensors"""
        self.pms5003.disconnect()
        self.bme680.disconnect()
        self.ens160.disconnect()
        print("All sensors disconnected")
    
    def read_all_sensors(self):
        """Read data from all connected sensors and combine results"""
        try:
            # Read each sensor
            pms_data = self.pms5003.read_data()
            bme_data = self.bme680.read_data()
            ens_data = self.ens160.read_data()
            
            with self.data_lock:
                self.pms5003_data = pms_data if pms_data else {}
                self.bme680_data = bme_data if bme_data else {}
                self.ens160_data = ens_data if ens_data else {}
                
                # Combine all data
                self.combined_data = {
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'pms5003': self.pms5003_data,
                    'bme680': self.bme680_data,
                    'ens160': self.ens160_data
                }
            
            return self.combined_data
        except Exception as e:
            print(f"Error reading sensors: {e}")
            return None
    
    def print_data(self, data):
        """Pretty print sensor data"""
        if not data:
            print("No data available")
            return
        
        print(f"\n{'='*60}")
        print(f"Sensor Reading - {data['timestamp']}")
        print(f"{'='*60}")
        
        # PMS5003 Data
        if data['pms5003']:
            print("\n[PMS5003 - Particulate Matter]")
            print(f"  PM1.0:  {data['pms5003'].get('pm1_atm', 'N/A')} µg/m³")
            print(f"  PM2.5:  {data['pms5003'].get('pm25_atm', 'N/A')} µg/m³")
            print(f"  PM10:   {data['pms5003'].get('pm10_atm', 'N/A')} µg/m³")
        else:
            print("\n[PMS5003 - Particulate Matter] - No data")
        
        # BME680 Data
        if data['bme680']:
            print("\n[BME680 - Environmental]")
            print(f"  Temperature: {data['bme680'].get('temperature', 'N/A')}°C")
            print(f"  Humidity:    {data['bme680'].get('humidity', 'N/A')}%")
            print(f"  Pressure:    {data['bme680'].get('pressure', 'N/A')} hPa")
            print(f"  Gas:         {data['bme680'].get('gas', 'N/A')} Ohms")
            print(f"  Altitude:    {data['bme680'].get('altitude', 'N/A')} m")
        else:
            print("\n[BME680 - Environmental] - No data")
        
        # ENS160 Data
        if data['ens160']:
            print("\n[ENS160 - Air Quality]")
            print(f"  AQI:  {data['ens160'].get('aqi', 'N/A')} ({data['ens160'].get('aqi_description', 'N/A')})")
            print(f"  TVOC: {data['ens160'].get('tvoc', 'N/A')} ppb")
            print(f"  eCO2: {data['ens160'].get('eco2', 'N/A')} ppm")
        else:
            print("\n[ENS160 - Air Quality] - No data")
        
        print(f"{'='*60}\n")
    
    def save_to_database(self, data):
        """Save combined sensor data to database"""
        if not data:
            return False
        
        try:
            pms = data.get('pms5003', {})
            bme = data.get('bme680', {})
            ens = data.get('ens160', {})
            
            db.insert_reading(
                pm1=pms.get('pm1_atm'),
                pm25=pms.get('pm25_atm'),
                pm10=pms.get('pm10_atm'),
                temperature=bme.get('temperature'),
                humidity=bme.get('humidity'),
                pressure=bme.get('pressure'),
                gas=bme.get('gas'),
                altitude=bme.get('altitude'),
                aqi=ens.get('aqi'),
                tvoc=ens.get('tvoc'),
                eco2=ens.get('eco2')
            )
            return True
        except Exception as e:
            print(f"Error saving to database: {e}")
            return False
    
    def read_continuous(self, interval=2, save_to_db=False, duration=None):
        """
        Read all sensors continuously
        
        Args:
            interval: Time between readings in seconds
            save_to_db: Save readings to database
            duration: Total duration to read in seconds (None = infinite)
        """
        start_time = time.time()
        
        try:
            while True:
                data = self.read_all_sensors()
                self.print_data(data)
                
                if save_to_db and data:
                    self.save_to_database(data)
                    print("✓ Data saved to database")
                
                time.sleep(interval)
                
                # Check if duration limit reached
                if duration and (time.time() - start_time) >= duration:
                    break
                    
        except KeyboardInterrupt:
            print("\n\nStopped by user")


def main():
    """Main function to demonstrate combined sensor usage"""
    
    # Create combined reader instance
    reader = CombinedSensorReader(
        pms5003_port='/dev/ttyS0',
        bme680_address=0x77,
        ens160_address=0x53
    )
    
    # Connect to all sensors
    if not reader.connect_all():
        print("Failed to connect to any sensor. Check connections.")
        return
    
    print("\nReading all sensor data...")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Read continuously every 2 seconds and save to database
        reader.read_continuous(interval=2, save_to_db=True)
    finally:
        # Ensure we disconnect properly
        reader.disconnect_all()


if __name__ == "__main__":
    main()
