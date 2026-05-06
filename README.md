# ESP32 Implementation Guide: LightchangerT

## Overview
This is the ESP32 port of LightchangerT, designed to detect gaming consoles on the local network and change the color of a WS2812B LED strip.

## Dependencies
The following libraries must be installed via the Arduino Library Manager:
1. **FastLED** (for LED control)
2. **ESPping** (for ICMP liveness checks)

## Hardware Setup
- **LED Strip**: WS2812B (NeoPixel)
- **Data Pin**: GPIO 13 (configurable in `config.h`)
- **Power**: External 5V power supply recommended for the LED strip.

## Configuration
Edit `config.h` to set your:
- WiFi SSID and Password.
- LED Pin and length.
- Custom colors.

## How it Works
1. **Scan**: Scans the subnet for MAC addresses matching the vendor OUIs.
2. **Verify**: Pings the identified devices to ensure they are not in deep sleep.
3. **Steam Check**: Uses mDNS and TCP port 27036 to find Steam devices.
4. **Priority**: The last device to respond to a ping takes control of the LED color.
5. **Idle**: Returns to the default color (White) if no active devices are found.
