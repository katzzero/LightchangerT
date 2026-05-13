# LightchangerT

Network-aware LED controller for gaming consoles. Detects when your PlayStation, Xbox, Nintendo Switch, Steam Deck, or Nvidia Shield comes online and changes your LED strip's color accordingly.

## Features

- **Dual platform**: Runs on Raspberry Pi (Python) or standalone on ESP32 (C++)
- **Multi-detection**: Static IP list, MAC OUI lookup, ARP scan, port probe, mDNS
- **Priority logic**: Last device to come online controls the LED color
- **Deep sleep safe**: ICMP ping verification before lighting up
- **Remote command**: Control ESP32 LEDs from another machine via TCP (`COLOR:blue`, `RGB:255,0,0`, `OFF`)
- **Dual-mode LED**: Raspberry Pi can mirror colors to a remote ESP32 (optional)
- **Captive portal**: Headless ESP32 setup — connect to "Lightchanger-Setup" AP, configure WiFi via browser
- **OTA updates**: Flash new firmware to ESP32 over WiFi (ArduinoOTA, port 3232)
- **Web UI**: Built-in configuration interface on both platforms
- **CI tested**: 74 unit tests + Arduino CLI compile on every push

## Supported Platforms

| Brand     | Color      | Detection Methods                 |
|-----------|------------|-----------------------------------|
| Sony      | Blue       | Static IP, MAC OUI                |
| Microsoft | Green      | Static IP, MAC OUI                |
| Nintendo  | Red        | Static IP, MAC OUI                |
| Steam     | Light Blue | Port probe (TCP 27015-27036), mDNS |
| Nvidia    | Light Green| Static IP, MAC OUI                |

## Directory Structure

```
LightchangerT/
├── main.py                 [main]   Python entry point (shim → python/main.py)
├── config.json             [main]   Shared configuration
├── python/                 [main]   All Python source code
│   ├── main.py                      Main game loop
│   ├── scanner.py                   ARP-based network discovery
│   ├── liveness.py                  ICMP ping validation
│   ├── steam_detector.py            Steam port probe + mDNS
│   ├── led_controller.py            LED drivers (FastLED/NeoPixel/RPi_WS281X)
│   ├── esp32_client.py              TCP client for remote ESP32 control
│   ├── web_config.py                Web configuration UI
│   ├── config_manager.py            Thread-safe singleton with atomic writes
│   ├── colors.py                    COLOR_MAP + BRAND_COLORS
│   └── tests/                       74 pytest tests
├── esp32/                 [ESP32]   All C++ source code
│   ├── esp32.ino                    Main sketch with OTA + command server
│   ├── config.h                     Hardware & network configuration
│   ├── config_manager.h             NVS-backed persistent settings
│   ├── led_controller.h             FastLED driver
│   ├── steam_detector.h             Multi-port Steam detection
│   ├── network_scanner.h            Static device validator
│   ├── liveness_engine.h            ESPPing ICMP check
│   ├── captive_portal.h             AP mode setup with web form
│   ├── web_ui.h                     HTML/JS configuration UI
│   ├── ota_fw_update.h              ArduinoOTA firmware update
│   ├── basic_auth.h                 Session auth + CSRF tokens
│   └── main.cpp                     Legacy stub (replaced by esp32.ino)
├── .github/workflows/ci.yml         CI pipeline (lint, test, compile)
└── README.md
```

## Quick Start (Python)

```bash
git clone https://github.com/katzzero/LightchangerT.git
cd LightchangerT
pip install -r requirements.txt
# Edit config.json with your network settings
python3 main.py
```

Enable the web UI in `config.json`:
```json
"web_config_enabled": true,
"web_config_port": 8080
```

## Quick Start (ESP32)

### Option 1: Arduino CLI
```bash
cd LightchangerT
arduino-cli compile --fqbn esp32:esp32:esp32 esp32/
arduino-cli upload -p <PORT> --fqbn esp32:esp32:esp32 esp32/
```

### Option 2: Arduino IDE
1. Open `esp32/esp32.ino`
2. Install libraries: FastLED 3.10.3, ESPing 1.0.5, ESPmDNS
3. Select board: ESP32 Dev Module
4. Upload

### First Boot (Captive Portal)
1. ESP32 starts an AP named **Lightchanger-Setup** (password: `lightchanger`)
2. Connect your phone/laptop to that WiFi
3. Open http://lightchanger.local in a browser
4. Enter your WiFi credentials and save
5. ESP32 reboots into STA mode

### OTA Updates
Once on WiFi, flash new firmware over the air:
- Arduino IDE: Tools → Port → Network Ports → lightchanger-esp32
- CLI: `arduino-cli upload --fqbn esp32:esp32:esp32 --port lightchanger-esp32.local`

## Remote Command Protocol

Control ESP32 LEDs from any machine on the network via TCP:

| Command            | Description                    | Example                        |
|--------------------|--------------------------------|--------------------------------|
| `COLOR:<name>`    | Set LED by named color         | `COLOR:blue`                   |
| `RGB:<r>,<g>,<b>` | Set LED by RGB values (0–255) | `RGB:255,0,0`                  |
| `OFF`              | Turn off LED strip             | `OFF`                          |
| `STATUS?`          | Query device state             | `STATUS?` → `STATUS:active`    |

```bash
echo 'COLOR:blue' | nc 192.168.1.50 10001
echo 'RGB:255,0,0' | nc 192.168.1.50 10001
```

From Python:
```python
from esp32_client import ESP32Client
client = ESP32Client("192.168.1.50", port=10001)
client.set_color("blue")
client.off()
print(client.get_status())
```

## Dual-Mode (Python + ESP32)

The Raspberry Pi can control local LEDs AND mirror colors to a remote ESP32 simultaneously:

```json
{
  "esp32_command": {
    "enabled": true,
    "host": "192.168.1.50",
    "port": 10001,
    "timeout": 5
  }
}
```

## Configuration (config.json)

```json
{
  "hardware": {
    "led_library": "FASTLED",
    "led_pin": 13,
    "num_leds": 30,
    "brightness": 128
  },
  "network": {
    "subnet": "192.168.1.0/24",
    "scan_interval_seconds": 30,
    "detection_mode": "HYBRID",
    "web_config_enabled": false,
    "web_config_port": 8080
  },
  "devices": {
    "static_list": [
      {"ip": "192.168.1.10", "mac": "AA:BB:CC:DD:EE:FF", "brand": "sony"}
    ],
    "steam_detection": {
      "method": "PORT_PROBE",
      "port": 27036
    }
  },
  "colors": {
    "sony": "blue",
    "microsoft": "green",
    "nintendo": "red",
    "steam": "light_blue",
    "nvidia": "light_green",
    "default": "white"
  },
  "esp32_command": {
    "enabled": false,
    "host": "192.168.1.50",
    "port": 10001
  }
}
```

## Web UI Endpoints (ESP32)

| Method | Path              | Description                |
|--------|-------------------|----------------------------|
| GET    | `/`               | Configuration page          |
| POST   | `/save`           | Add/edit device or set port |
| POST   | `/clear`          | Clear all devices           |
| GET    | `/api/devices`    | List devices as JSON        |
| GET    | `/api/config`     | Get command port setting    |
| GET    | `/api/device?idx=N` | Get single device         |
| DELETE | `/api/device?idx=N` | Delete device            |

## Testing

```bash
# Python (74 tests)
pytest python/tests/ -v

# ESP32 compile check
arduino-cli compile --fqbn esp32:esp32:esp32 esp32/
```

## License

MIT
