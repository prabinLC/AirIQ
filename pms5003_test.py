#!/usr/bin/env python3
"""
PMS5003 Diagnostic Script
Tests serial connection and displays raw data
"""

import serial
import time

port = '/dev/ttyAMA0'
baudrate = 9600

print(f"Opening serial port {port}...")
try:
    ser = serial.Serial(port, baudrate, timeout=2)
    print(f"✓ Serial port opened successfully")
    print(f"  Baudrate: {baudrate}")
    print(f"  Timeout: 2 seconds")
    print()
    
    # Wait for sensor to stabilize
    print("Waiting 3 seconds for sensor to stabilize...")
    time.sleep(3)
    
    # Try to read raw data
    print("\nAttempting to read raw data (10 seconds)...")
    print("If you see hex values below, the sensor is transmitting.")
    print("-" * 60)
    
    start_time = time.time()
    byte_count = 0
    
    while (time.time() - start_time) < 10:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            byte_count += len(data)
            # Print hex values
            hex_string = ' '.join([f'{b:02X}' for b in data])
            print(hex_string)
        time.sleep(0.1)
    
    print("-" * 60)
    print(f"\nTotal bytes received: {byte_count}")
    
    if byte_count == 0:
        print("\n⚠ NO DATA RECEIVED")
        print("\nPossible issues:")
        print("1. Check wiring - TX/RX might be swapped")
        print("   - PMS5003 TXD should connect to Pi RXD (GPIO 15, Pin 10)")
        print("   - PMS5003 RXD should connect to Pi TXD (GPIO 14, Pin 8)")
        print("2. Check power - sensor needs 5V")
        print("3. Try different serial port (e.g., /dev/ttyAMA0)")
        print("4. Sensor might be in sleep mode - try resetting it")
    elif byte_count < 32:
        print("\n⚠ VERY LITTLE DATA - possible connection issue")
    else:
        print("\n✓ Data is being received!")
        print("If you see repeating pattern starting with '42 4D', the sensor is working.")
    
    ser.close()
    print("\nSerial port closed.")
    
except serial.SerialException as e:
    print(f"✗ Error: {e}")
except KeyboardInterrupt:
    print("\n\nStopped by user")
    ser.close()
