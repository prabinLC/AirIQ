#!/usr/bin/env python3
"""
PMS5003 Air Quality Sensor Reader for Raspberry Pi
Reads PM1.0, PM2.5, and PM10 particulate matter concentrations
"""

import serial
import struct
import time

class PMS5003:
    """Class to read data from PMS5003 air quality sensor"""
    
    # Start bytes for PMS5003 data frame
    START_BYTE_1 = 0x42
    START_BYTE_2 = 0x4d
    
    def __init__(self, port='/dev/ttyAMA0', baudrate=9600, timeout=2):
        """
        Initialize PMS5003 sensor
        
        Args:
            port: Serial port (default: /dev/ttyAMA0 for Raspberry Pi)
            baudrate: Communication speed (default: 9600)
            timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        
    def connect(self):
        """Open serial connection to the sensor"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            # Flush any pending data in the buffer
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            print(f"Connected to PMS5003 on {self.port}")
            time.sleep(2)  # Allow sensor to stabilize
            return True
        except serial.SerialException as e:
            print(f"Error connecting to sensor: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Disconnected from sensor")
    
    def read_data(self):
        """
        Read and parse data from PMS5003 sensor
        
        Returns:
            dict: Dictionary containing PM values or None if read fails
        """
        if not self.serial or not self.serial.is_open:
            return None
        
        try:
            # Read until we find the start bytes
            sync_attempts = 0
            while sync_attempts < 100:
                byte1 = self.serial.read(1)
                if not byte1:
                    return None
                
                if byte1[0] == self.START_BYTE_1:
                    byte2 = self.serial.read(1)
                    if byte2 and byte2[0] == self.START_BYTE_2:
                        break
                sync_attempts += 1
            
            if sync_attempts >= 100:
                return None
            
            # Read frame length (2 bytes)
            frame_length_bytes = self.serial.read(2)
            if len(frame_length_bytes) != 2:
                return None
            
            frame_length = struct.unpack('>H', frame_length_bytes)[0]
            
            # Validate frame length
            if frame_length > 64:
                return None
            
            # Read the rest of the frame
            frame_data = self.serial.read(frame_length)
            
            if len(frame_data) < 12:
                return None
            
            # Parse the data (first 12 bytes contain PM values)
            data = struct.unpack('>HHHHHH', frame_data[0:12])
            
            # Return parsed data
            return {
                'pm1_cf': data[0],
                'pm25_cf': data[1],
                'pm10_cf': data[2],
                'pm1_atm': data[3],
                'pm25_atm': data[4],
                'pm10_atm': data[5],
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
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
                    print(f"PM1.0:  {data['pm1_atm']} µg/m³")
                    print(f"PM2.5:  {data['pm25_atm']} µg/m³")
                    print(f"PM10:   {data['pm10_atm']} µg/m³")
                else:
                    print("Failed to read data")
                
                time.sleep(interval)
                
                # Check if duration limit reached
                if duration and (time.time() - start_time) >= duration:
                    break
                    
        except KeyboardInterrupt:
            print("\n\nStopped by user")


def main():
    """Main function to demonstrate PMS5003 usage"""
    
    # Create sensor instance
    sensor = PMS5003(port='/dev/ttyAMA0', baudrate=9600)
    
    # Connect to sensor
    if not sensor.connect():
        print("Failed to connect to sensor. Check connections and serial port configuration.")
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
