"""Integration tests for the full pipeline."""
import pytest
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner import NetworkScanner
from liveness import LivenessEngine
from steam_detector import SteamDetector
from config_manager import ConfigManager


class TestFullPipeline:
    def test_scanner_and_liveness_work_together(self, tmp_path):
        config_file = tmp_path / "config.json"
        config = {
            "devices": {
                "static_list": [
                    {"ip": "127.0.0.1", "mac": "AA:BB:CC:DD:EE:FF", "brand": "sony"},
                ],
                "oui_prefixes": {},
            },
            "network": {"subnet": "127.0.0.0/8"},
        }
        config_file.write_text(json.dumps(config))

        s = NetworkScanner(config=config)
        devices = s.scan()
        assert len(devices) >= 1

        engine = LivenessEngine(config=config)
        for dev in devices:
            result = engine.is_alive(dev["ip"])
            assert isinstance(result, bool)

    def test_steam_detector_with_empty_ips(self):
        config = {"steam_detection": {"method": "PORT_PROBE", "port": 65535}}
        sd = SteamDetector(config)
        result = sd.detect([])
        assert result is None

    def test_steam_detector_with_config(self, tmp_path):
        config = {
            "devices": {
                "steam_detection": {
                    "method": "PORT_PROBE",
                    "port": 99999,
                    "mdns_hostname": "steamdeck.local",
                }
            }
        }
        sd = SteamDetector(config)
        assert sd.method == "PORT_PROBE"
        assert sd.port == 99999

    def test_config_manager_is_singleton(self):
        cm1 = ConfigManager()
        cm2 = ConfigManager()
        assert cm1 is cm2

    def test_game_loop_flow(self, tmp_path):
        config_file = tmp_path / "config.json"
        config = {
            "devices": {
                "static_list": [
                    {"ip": "127.0.0.1", "mac": "AA:BB:CC:DD:EE:FF", "brand": "sony"},
                ],
                "oui_prefixes": {},
            },
            "network": {"subnet": "127.0.0.0/8"},
        }
        config_file.write_text(json.dumps(config))

        s = NetworkScanner(config=config)
        engine = LivenessEngine(config=config)
        sd = SteamDetector({"steam_detection": {"method": "PORT_PROBE", "port": 65535}})

        candidates = s.scan()
        assert isinstance(candidates, list)

        if any(d["ip"] == "127.0.0.1" for d in candidates):
            alive = engine.is_alive("127.0.0.1")
            assert isinstance(alive, bool)

        active_ips = [d["ip"] for d in candidates]
        steam_result = sd.detect(active_ips)
        assert steam_result is None or isinstance(steam_result, dict)

        if candidates:
            last = candidates[-1]["brand"]
            assert isinstance(last, str)

    def test_all_components_have_expected_attributes(self):
        from colors import BRAND_COLORS, Color
        from led_controller import LEDController, get_led_controller, _to_rgb, COLOR_MAP

        assert callable(NetworkScanner)
        assert callable(LivenessEngine)
        assert callable(SteamDetector)
        assert callable(ConfigManager)
        assert callable(LEDController)
        assert callable(get_led_controller)
        assert callable(_to_rgb)
        assert isinstance(COLOR_MAP, dict)
        assert isinstance(BRAND_COLORS, dict)

    def test_config_manager_deep_merge(self):
        """Verify deep merge doesn't destroy sibling keys."""
        cm = ConfigManager()
        cm._instance = None
        ConfigManager._instance = None

        cm2 = ConfigManager()
        cm2._config = {
            "network": {"subnet": "192.168.1.0/24", "scan_interval_seconds": 30},
            "devices": {"static_list": [{"ip": "1.1.1.1", "brand": "sony"}]},
        }
        cm2.update({"network": {"scan_interval_seconds": 60}})
        assert cm2._config["network"]["subnet"] == "192.168.1.0/24"
        assert cm2._config["network"]["scan_interval_seconds"] == 60
        assert len(cm2._config["devices"]["static_list"]) == 1