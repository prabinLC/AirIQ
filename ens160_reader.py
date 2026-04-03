#!/usr/bin/env python3
"""
ENS160 Air Quality Sensor Reader for Raspberry Pi
Reads AQI, eCO2, and TVOC measurements
Connected to I2C GPIO 2 (SDA) and GPIO 3 (SCL)
"""

import time

class ENS160Reader:
    """Class to read data from ENS160 air quality sensor"""
    
    def __init__(self, i2c_address=0x53):
        """
        Initialize ENS160 sensor
        
        Args:
            i2c_address: I2C address of ENS160 (default: 0x53, alt: 0x52)
        """
        self.i2c_address = i2c_address
        self.sensor = None
        self.i2c = None
        
    def connect(self, shared_i2c=None):
        """Initialize I2C connection and sensor"""
        try:
            import board
            import busio
            import adafruit_ens160
        except ImportError as e:
            print(f"Could not import I2C libraries: {e}")
            return False
        
        addresses_to_try = [self.i2c_address]
        # Add alternate address if primary doesn't work
        alt_addr = 0x52 if self.i2c_address == 0x53 else 0x53
        if alt_addr not in addresses_to_try:
            addresses_to_try.append(alt_addr)
        
        for addr in addresses_to_try:
            try:
                # Use shared I2C bus if provided, otherwise create one
                if shared_i2c is not None:
                    self.i2c = shared_i2c
                    self._owns_i2c = False
                else:
                    self.i2c = busio.I2C(board.SCL, board.SDA)
                    self._owns_i2c = True

                # Initialize ENS160 sensor
                self.sensor = adafruit_ens160.ENS160(self.i2c, address=addr)

                print(f"Connected to ENS160 at address 0x{addr:02x}")
                self.i2c_address = addr
                time.sleep(1)  # Allow sensor to stabilize
                return True
            except Exception as e:
                if addr == addresses_to_try[-1]:
                    # This was the last address to try
                    print(f"Error connecting to ENS160 on addresses {addresses_to_try}: {e}")
                    return False
                # Try next address
                continue
        return False
    
    def disconnect(self):
        """Close I2C connection"""
        if self.i2c and getattr(self, '_owns_i2c', True):
            self.i2c.deinit()
        print("Disconnected from ENS160")
    
    def get_aqi_description(self, aqi):
        """Get human-readable description for AQI value"""
        aqi_levels = {
            1: 'Excellent',
            2: 'Good',
            3: 'Moderate',
            4: 'Poor',
            5: 'Unhealthy'
        }
        return aqi_levels.get(aqi, 'Unknown')
    
    def read_data(self):
        """
        Read and return data from ENS160 sensor
        
        Returns:
            dict: Dictionary containing sensor readings or None if read fails
        
        AQI Standard:
        - ENS160 reports AQI on 1-5 scale per UPE (Ultra-Low Power Environmental) standard
        - 1: Excellent (0-50 ePPM equivalent)
        - 2: Good (51-100 ePPM)
        - 3: Moderate (101-150 ePPM)
        - 4: Poor (151-200 ePPM)
        - 5: Unhealthy (>200 ePPM)
        """
        if not self.sensor:
            print("Sensor not connected")
            return None
        
        try:
            # Read all sensor values
            aqi_raw = self.sensor.AQI
            # Clamp AQI to valid 1-5 range (sometimes sensor returns values outside range)
            aqi = max(1, min(5, int(aqi_raw)))
            tvoc = self.sensor.TVOC
            eco2 = self.sensor.eCO2
            
            return {
                'aqi': aqi,
                'aqi_description': self.get_aqi_description(aqi),
                'tvoc': round(tvoc, 2),
                'eco2': round(eco2, 2),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            print(f"Error reading ENS160 data: {e}")
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
                    print(f"AQI:         {data['aqi']} ({data['aqi_description']})")
                    print(f"TVOC:        {data['tvoc']} ppb")
                    print(f"eCO2:        {data['eco2']} ppm")
                else:
                    print("Failed to read data")
                
                time.sleep(interval)
                
                # Check if duration limit reached
                if duration and (time.time() - start_time) >= duration:
                    break
                    
        except KeyboardInterrupt:
            print("\n\nStopped by user")


def main():
    """Main function to demonstrate ENS160 usage"""
    
    # Create sensor instance
    sensor = ENS160Reader(i2c_address=0x53)
    
    # Connect to sensor
    if not sensor.connect():
        print("Failed to connect to sensor. Check I2C connections and address.")
        return
    
    print("\nReading air quality data...")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Read continuously every 2 seconds
        sensor.read_continuous(interval=2)
    finally:
        # Ensure we disconnect properly
        sensor.disconnect()


if __name__ == "__main__":
    main()
