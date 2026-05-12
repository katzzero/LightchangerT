# LightchangerT

LightchangerT is a network-aware LED controller for gaming consoles. It detects when your gaming devices (PlayStation, Xbox, Nintendo Switch, Steam Deck, etc.) are online and changes the color of your LED strip accordingly.

## Features

- **Multi-Platform Support**: Works on Raspberry Pi (Python) and ESP32 (C++).
- **Deep Sleep Detection**: Uses ICMP ping verification to ensure devices are truly awake.
- **Priority Logic**: The last device to come online controls the LED color.
- **Web Configuration**: Optional built-in web interface to manage devices and colors without editing config files.
- **Custom Colors**: Fully customizable RGB color mapping for each brand.
- **Steam Detection**: Concurrent multi-port probing + mDNS with retry logic.
- **Atomic Config Writes**: Prevents config corruption on unexpected shutdowns.

## Supported Platforms

| Brand | Platform | Color |
|-------|----------|-------|
| Sony | PlayStation | Blue |
| Microsoft | Xbox | Green |
| Nintendo | Switch | Red |
| Steam | Steam Deck / PC | Light Blue |
| Nvidia | Shield | Light Green |

## Installation

### Python (Raspberry Pi / Linux)

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd LightchangerT
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Edit `config.json` with your network settings and LED hardware configuration.

4. Test:
   ```bash
   python3 main.py
   ```

5. (Optional) Install as a systemd service:
   ```bash
   sudo cp lightchanger.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable lightchanger
   sudo systemctl start lightchanger
   sudo systemctl status lightchanger
   ```

### ESP32

1. Open the project in Arduino IDE or PlatformIO.
2. Install dependencies via Library Manager:
   - **FastLED** (3.10.3)
   - **ESPping** (1.0.5)
   - **ESPmDNS** (1.1.0)
3. Edit `config.h` with your WiFi credentials and hardware settings.
4. Upload to your ESP32 board.

## Configuration

Edit `config.json` (Python) or `config.h` (ESP32) to:
- Change the LED pin and count
- Customize brand-to-color mapping
- Set static device IPs and OUI prefixes
- Enable the web configuration interface

### Web Config (Python)

To enable the web interface, set in `config.json`:
```json
"web_config_enabled": true,
"web_config_port": 80
```

Then restart the application. Access `http://<raspberry-pi-ip>` in your browser.

### Web API Endpoints (ESP32)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main configuration UI |
| GET | `/api/devices` | List all devices as JSON |
| GET | `/api/device?idx=N` | Get device at index N |
| DELETE | `/api/device?idx=N` | Delete device at index N |
| POST | `/save` | Save device (params: `ip`, `brand`) |
| POST | `/clear` | Clear all devices |

## Hardware Wiring

- **WS2812B / NeoPixel**: Data pin → GPIO13 (default), 5V and GND connected
- Ensure a **330Ω resistor** on the data line and a **1000µF capacitor** across power for stable operation.

## Architecture

```
Scan ARP table → Verify Liveness (ping) → Check Steam port → Determine Priority → Set LED
```

### Components

| File | Purpose |
|------|---------|
| `main.py` | Entry point, GameStateController, main loop |
| `led_controller.py` | LED drivers (FastLED/NeoPixel/RPi_WS281X) |
| `scanner.py` | Network device discovery (ARP + static list) |
| `config_manager.py` | Thread-safe singleton config management |
| `liveness.py` | ICMP ping device validation |
| `steam_detector.py` | Steam detection (ports + mDNS) |
| `web_config.py` | HTTP web configuration UI |
| `colors.py` | Shared color definitions |

## CI

GitHub Actions runs on every push/PR:
- **Python**: syntax check (`py_compile`) + pytest suite
- **ESP32**: Arduino CLI compilation
- **Format**: ruff linting

## License

MIT