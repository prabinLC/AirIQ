#!/usr/bin/env python3
"""
BME680 Environmental Sensor Reader for Raspberry Pi
Reads temperature, humidity, pressure, gas resistance, and altitude
Connected to I2C GPIO 2 (SDA) and GPIO 3 (SCL)
"""

import board
import busio
import adafruit_bme680
import time

class BME680Reader:
    """Class to read data from BME680 environmental sensor"""
    
    def __init__(self, i2c_address=0x77, temperature_offset=0):
        """
        Initialize BME680 sensor
        
        Args:
            i2c_address: I2C address of BME680 (default: 0x77, alt: 0x76)
            temperature_offset: Temperature calibration offset in Celsius
        """
        self.i2c_address = i2c_address
        self.temperature_offset = temperature_offset
        self.sensor = None
        self.i2c = None
        
    def connect(self, shared_i2c=None):
        """Initialize I2C connection and sensor"""
        try:
            # Use shared I2C bus if provided, otherwise create one
            if shared_i2c is not None:
                self.i2c = shared_i2c
                self._owns_i2c = False
            else:
                self.i2c = busio.I2C(board.SCL, board.SDA)
                self._owns_i2c = True
            
            # Initialize BME680 sensor
            self.sensor = adafruit_bme680.Adafruit_BME680_I2C(
                self.i2c,
                address=self.i2c_address
            )
            
            # Set sea level pressure (adjust based on location)
            self.sensor.sea_level_pressure = 1013.25
            
            print(f"Connected to BME680 at address 0x{self.i2c_address:02x}")
            time.sleep(1)  # Allow sensor to stabilize
            return True
        except Exception as e:
            print(f"Error connecting to BME680: {e}")
            return False
    
    def disconnect(self):
        """Close I2C connection"""
        if self.i2c and getattr(self, '_owns_i2c', True):
            self.i2c.deinit()
        print("Disconnected from BME680")
    
    def read_data(self):
        """
        Read and return data from BME680 sensor
        
        Returns:
            dict: Dictionary containing sensor readings or None if read fails
        """
        if not self.sensor:
            print("Sensor not connected")
            return None
        
        try:
            # Read all sensor values
            temperature = self.sensor.temperature + self.temperature_offset
            humidity = self.sensor.humidity
            pressure = self.sensor.pressure
            gas = self.sensor.gas
            altitude = self.sensor.altitude
            
            return {
                'temperature': round(temperature, 2),
                'humidity': round(humidity, 2),
                'pressure': round(pressure, 2),
                'gas': round(gas, 2),
                'altitude': round(altitude, 2),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            print(f"Error reading BME680 data: {e}")
            return None
    
    def read_continuous(self, interval=1, duration=None):
        """
        Read data continuously from sensor
        
        Args:
            interval: Time between readings in seconds
            duration: Total duration to read in seconds (None = infinite)
        """
        start_time = time.time()
        
        try:
            while True:
                data = self.read_data()
                
                if data:
                    print(f"\n[{data['timestamp']}]")
                    print(f"Temperature: {data['temperature']:.2f}°C")
                    print(f"Humidity:    {data['humidity']:.2f}%")
                    print(f"Pressure:    {data['pressure']:.2f} hPa")
                    print(f"Gas:         {data['gas']:.2f} Ohms")
                    print(f"Altitude:    {data['altitude']:.2f} m")
                else:
                    print("Failed to read data")
                
                time.sleep(interval)
                
                # Check if duration limit reached
                if duration and (time.time() - start_time) >= duration:
                    break
                    
        except KeyboardInterrupt:
            print("\n\nStopped by user")


def main():
    """Main function to demonstrate BME680 usage"""
    
    # Create sensor instance
    sensor = BME680Reader(i2c_address=0x77, temperature_offset=0)
    
    # Connect to sensor
    if not sensor.connect():
        print("Failed to connect to sensor. Check I2C connections and address.")
        return
    
    print("\nReading environmental data...")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Read continuously every 2 seconds
        sensor.read_continuous(interval=2)
    finally:
        # Ensure we disconnect properly
        sensor.disconnect()


if __name__ == "__main__":
    main()
