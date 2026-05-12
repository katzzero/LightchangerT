# LightchangerT

LightchangerT is a network-aware LED controller for gaming consoles. It detects when your gaming devices (PlayStation, Xbox, Nintendo Switch, Steam Deck, etc.) are online and changes the color of your LED strip accordingly.

## Features
- **Multi-Platform Support**: Works on Raspberry Pi (Python) and ESP32 (C++).
- **Deep Sleep Detection**: Uses ping verification to ensure devices are truly awake.
- **Priority Logic**: The last device to come online controls the LED color.
- **Web Configuration**: Optional built-in web interface to manage devices and colors without editing config files.
- **Custom Colors**: Fully customizable RGB color mapping for each brand.

## Supported Platforms
- **Sony (PlayStation)**: Blue
- **Microsoft (Xbox)**: Green
- **Nintendo (Switch)**: Red
- **Steam**: Light Blue
- **Nvidia (Shield)**: Light Green

## Installation

### Python (Raspberry Pi / Linux)
1. Clone the repository.
2. Install dependencies: `pip install zeroconf` (optional for mDNS).
3. Edit `config.json` with your network settings.
4. Run `python3 main.py`.

### ESP32
1. Open the project in Arduino IDE or PlatformIO.
2. Install dependencies: **FastLED**, **ESPping**, **ESPAsyncWebServer**.
3. Edit `config.h` with your WiFi credentials.
4. Upload to your ESP32 board.

## Configuration
Edit `config.json` (Python) or `config.h` (ESP32) to:
- Change the LED Pin and Count.
- Customize Colors.
- Set Static Device IPs.
- Enable the Web Configuration Interface.

## Web Config (Python)
To enable the web interface, set in `config.json`:
```json
"web_config_enabled": true,
"web_config_port": 80
```
Then restart the application.

## License
MIT