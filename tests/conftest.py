import os
import sys
import json
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from led_controller import LEDController, COLOR_MAP, Color
from scanner import NetworkScanner
from steam_detector import SteamDetector, SteamServiceListener
from liveness import LivenessEngine
from config_manager import ConfigManager

# --- Fixtures ---

@pytest.fixture
def sample_config():
    return {
        "hardware": {
            "led_pin": 13,
            "num_leds": 30,
            "brightness": 128,
            "led_library": "FASTLED"
        },
        "devices": {
            "steam_detection": {
                "method": "PORT_PROBE",
                "port": 27036,
                "mdns_hostname": "steamdeck.local",
                "probe_timeout": 1,
                "retries": 2
            },
            "static_list": [
                {"mac": "00:11:22:33:44:55", "brand": "sony", "ip": "192.168.1.10"},
                {"mac": "66:77:88:99:AA:BB", "brand": "microsoft", "ip": "192.168.1.11"}
            ],
            "oui_prefixes": {
                "sony": ["00:04:1F", "00:13:15"],
                "microsoft": ["00:0D:3A", "00:12:5A"],
                "nintendo": ["00:09:BF"],
                "nvidia": ["00:04:4B"]
            }
        },
        "network": {
            "subnet": "192.168.1.0/24",
            "scan_interval_seconds": 30,
            "web_config_enabled": False,
            "web_config_port": 80
        },
        "colors": {
            "sony": "blue",
            "microsoft": "green",
            "nintendo": "red",
            "steam": "light_blue",
            "nvidia": "light_green",
            "default": "white"
        }
    }


class MockLEDController(LEDController):
    """Mock LED controller that stores last color for testing."""
    def __init__(self, config=None):
        self.last_color = None
        self.off_called = False

    def set_color(self, color_name):
        self.last_color = color_name

    def off(self):
        self.off_called = True


@pytest.fixture
def mock_led():
    return MockLEDController()


# --- Fixtures end ---
