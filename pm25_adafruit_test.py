#!/usr/bin/env python3
"""
Test PM2.5 sensor using Adafruit PM25 UART library
For RPi 5 with /dev/ttyAMA0
"""

import time
import serial
from adafruit_pm25.uart import PM25_UART

print("=" * 60)
print("PM2.5 SENSOR TEST - Adafruit UART Library")
print("=" * 60)

# For RPi 5, use /dev/ttyAMA0
uart = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=0.25)

print(f"\n✓ Serial port opened: /dev/ttyAMA0")
print(f"  Baudrate: 9600")
print(f"  Timeout: 0.25s")

# Create PM25 object
reset_pin = None
pm25 = PM25_UART(uart, reset_pin)

print(f"\n✓ PM25_UART object created")
print(f"\nWaiting for sensor data (5 attempts)...\n")

success = False
for attempt in range(5):
    try:
        print(f"Attempt {attempt + 1}/5: ", end="")
        aqdata = pm25.read()
        
        print("✅ SUCCESS! Got data:\n")
        
        print("Concentration Units (standard)")
        print("---------------------------------------")
        print("PM 1.0:  %d µg/m³" % aqdata["pm10 standard"])
        print("PM 2.5:  %d µg/m³" % aqdata["pm25 standard"])
        print("PM 10:   %d µg/m³" % aqdata["pm100 standard"])
        
        print("\nConcentration Units (environmental)")
        print("---------------------------------------")
        print("PM 1.0:  %d µg/m³" % aqdata["pm10 env"])
        print("PM 2.5:  %d µg/m³" % aqdata["pm25 env"])
        print("PM 10:   %d µg/m³" % aqdata["pm100 env"])
        
        print("\nParticle Counts")
        print("---------------------------------------")
        print("Particles > 0.3µm / 0.1L air: %d" % aqdata["particles 03um"])
        print("Particles > 0.5µm / 0.1L air: %d" % aqdata["particles 05um"])
        print("Particles > 1.0µm / 0.1L air: %d" % aqdata["particles 10um"])
        print("Particles > 2.5µm / 0.1L air: %d" % aqdata["particles 25um"])
        print("Particles > 5.0µm / 0.1L air: %d" % aqdata["particles 50um"])
        print("Particles > 10µm / 0.1L air:  %d" % aqdata["particles 100um"])
        
        success = True
        break
        
    except RuntimeError as e:
        print(f"❌ No data (RuntimeError: {e})")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
    
    time.sleep(1)

uart.close()

print("\n" + "=" * 60)
if success:
    print("✅ SENSOR WORKING!")
    print("=" * 60)
else:
    print("❌ SENSOR NOT RESPONDING")
    print("=" * 60)
    print("\nDiagnostics:")
    print("1. Is sensor LED on?")
    print("2. Is 5V connected to sensor PIN 2?")
    print("3. Is TXD (sensor PIN 4) connected to GPIO 14?")
    print("4. Is RXD (sensor PIN 3) connected to GPIO 15?")
    print("5. Try power cycling the sensor")
