#!/usr/bin/env python3
"""
I2C Scanner - Finds all connected I2C devices 
Helps identify available addresses for sensors
"""

import board
import busio

try:
    print("=" * 60)
    print("I2C DEVICE SCANNER")
    print("=" * 60)
    print("\nInitializing I2C bus...")
    i2c = busio.I2C(board.SCL, board.SDA)
    print("✓ I2C bus initialized successfully\n")
    
    print("Scanning addresses 0x00 to 0x7F...\n")
    print("Address | Device Found")
    print("--------|--------------------")
    
    found_devices = []
    for addr in range(128):
        addresses = i2c.scan()
        if addr in addresses:
            device_name = {
                0x52: "ENS160 (alternate)",
                0x53: "ENS160 (default)",
                0x76: "BME680 (alternate)",
                0x77: "BME680 (default)",
            }.get(addr, "Unknown device")
            print(f"0x{addr:02X}   | {device_name}")
            found_devices.append(addr)
    
    print("--------|--------------------")
    
    if found_devices:
        print(f"\n✓ Found {len(found_devices)} I2C device(s):")
        for addr in found_devices:
            print(f"  → 0x{addr:02X}")
    else:
        print("\n❌ No I2C devices found!")
        print("\nTroubleshooting:")
        print("1. Enable I2C in raspi-config (Interface Options)")
        print("2. Check sensor power supply (3.3V)")
        print("3. Verify SDA (pin 3) and SCL (pin 5) wiring")
        print("4. Check for loose connections")
    
    i2c.deinit()
    print("\n" + "=" * 60)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nMake sure you're running on a Raspberry Pi with I2C enabled")
    print("=" * 60)
