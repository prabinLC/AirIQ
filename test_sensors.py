#!/usr/bin/env python3
"""
Quick sensor connectivity test for AirIQ
Tests PMS5003, BME680, and ENS160 connections

SENSOR CONFIGURATION:
  PMS5003:  Serial port /dev/ttyAMA0 (Particulate Matter)
  BME680:   I2C address 0x77 or 0x76 (Temperature/Humidity/Pressure)
  ENS160:   I2C address 0x53 or 0x52 (Air Quality/eCO2/TVOC)
"""

import time
from pms5003_reader import PMS5003
from bme680_reader import BME680Reader
from ens160_reader import ENS160Reader

def test_pms5003():
    """Test PMS5003 sensor"""
    print("\n🔍 Testing PMS5003 (PM sensor)...")
    pms = PMS5003(port='/dev/ttyAMA0', baudrate=9600)
    try:
        if pms.connect():
            print("  ✅ Connected to PMS5003")
            time.sleep(2)
            data = pms.read_data()
            if data:
                print(f"  ✅ Data read successfully:")
                print(f"     PM1.0: {data.get('pm1_atm', '?')} µg/m³")
                print(f"     PM2.5: {data.get('pm25_atm', '?')} µg/m³")
                print(f"     PM10:  {data.get('pm10_atm', '?')} µg/m³")
                return True
            else:
                print("  ❌ Failed to read data from PMS5003")
                return False
        else:
            print("  ❌ Failed to connect to PMS5003")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    finally:
        pms.disconnect()

def test_bme680():
    """Test BME680 sensor with fallback"""
    print("\n🔍 Testing BME680 (Temperature/Humidity/Pressure)...")
    bme = BME680Reader(i2c_address=0x77)
    try:
        if bme.connect():
            print("  ✅ Connected to BME680")
            time.sleep(1)
            data = bme.read_data()
            if data:
                print(f"  ✅ Data read successfully:")
                print(f"     Temperature: {data.get('temperature', '?')}°C")
                print(f"     Humidity:    {data.get('humidity', '?')}%")
                print(f"     Pressure:    {data.get('pressure', '?')} hPa")
                print(f"     Altitude:    {data.get('altitude', '?')} m")
                print(f"     Gas:         {data.get('gas', '?')} Ω")
                return True
            else:
                print("  ❌ Failed to read data from BME680")
                return False
        else:
            print("  ❌ Failed to connect to BME680")
            print("     Troubleshooting:")
            print("     - Check I2C is enabled (raspi-config)")
            print("     - Verify wiring: SDA→GPIO2, SCL→GPIO3")
            print("     - Check 3.3V power supply to sensor")
            print("     - Run: i2cdetect -y 1  (to find device address)")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    finally:
        try:
            bme.disconnect()
        except:
            pass

def test_ens160():
    """Test ENS160 sensor with fallback"""
    print("\n🔍 Testing ENS160 (Air Quality/eCO2/TVOC)...")
    ens = ENS160Reader(i2c_address=0x53)
    try:
        if ens.connect():
            print("  ✅ Connected to ENS160")
            time.sleep(2)
            data = ens.read_data()
            if data:
                print(f"  ✅ Data read successfully:")
                print(f"     AQI:  {data.get('aqi', '?')} ({data.get('aqi_description', '?')})")
                print(f"     eCO2: {data.get('eco2', '?')} ppm")
                print(f"     TVOC: {data.get('tvoc', '?')} ppb")
                return True
            else:
                print("  ❌ Failed to read data from ENS160")
                return False
        else:
            print("  ❌ Failed to connect to ENS160")
            print("     Troubleshooting:")
            print("     - Check I2C is enabled (raspi-config)")
            print("     - Verify wiring: SDA→GPIO2, SCL→GPIO3")
            print("     - Check 3.3V power supply to sensor")
            print("     - Run: i2cdetect -y 1  (to find device address)")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    finally:
        try:
            ens.disconnect()
        except:
            pass

if __name__ == '__main__':
    print("=" * 50)
    print("AirIQ Sensor Connectivity Test")
    print("=" * 50)
    print("\nSensor Configuration:")
    print("  PMS5003:  /dev/ttyAMA0 (Particulate Matter)")
    print("  BME680:   0x77/0x76 on I2C (Temperature/Humidity)")
    print("  ENS160:   0x53/0x52 on I2C (Air Quality)")
    print("=" * 50)
    
    results = {
        'PMS5003': test_pms5003(),
        'BME680':  test_bme680(),
        'ENS160':  test_ens160(),
    }
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for sensor, status in results.items():
        symbol = "✅" if status else "❌"
        addr_info = {
            'PMS5003': '(/dev/ttyAMA0)',
            'BME680': '(0x77)',
            'ENS160': '(0x53)',
        }
        print(f"{symbol} {sensor} {addr_info.get(sensor, '')}: {'CONNECTED' if status else 'FAILED'}")
    
    all_ok = all(results.values())
    print("\n" + ("✅ All sensors ready!\n" if all_ok else "❌ Some sensors failed — check connections\n"))
