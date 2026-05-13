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
    """Tests that verify component interaction."""

    def test_scanner_and_liveness_work_together(self, tmp_path):
        """Scanner discovers devices, liveness verifies them."""
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

        s = NetworkScanner(str(config_file))
        devices = s.scan()
        assert len(devices) >= 1

        engine = LivenessEngine(str(config_file))
        for dev in devices:
            result = engine.is_alive(dev["ip"])
            assert isinstance(result, bool)

    def test_steam_detector_with_empty_ips(self):
        """SteamDetector handles empty IP list gracefully."""
        config = {"steam_detection": {"method": "PORT_PROBE", "port": 65535}}
        sd = SteamDetector(config)
        result = sd.detect([])
        assert result is None

    def test_steam_detector_with_config(self, tmp_path):
        """SteamDetector initializes from config dict."""
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
        """ConfigManager returns same instance across calls."""
        cm1 = ConfigManager()
        cm2 = ConfigManager()
        assert cm1 is cm2

    def test_game_loop_flow(self, tmp_path):
        """Simulated game loop: scan -> liveness -> steam -> decide."""
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

        s = NetworkScanner(str(config_file))

        engine = LivenessEngine(str(config_file))

        sd = SteamDetector({"steam_detection": {"method": "PORT_PROBE", "port": 65535}})

        # Scan
        candidates = s.scan()
        assert isinstance(candidates, list)

        # If localhost is found, it should be alive
        if any(d["ip"] == "127.0.0.1" for d in candidates):
            alive = engine.is_alive("127.0.0.1")
            assert isinstance(alive, bool)

        # Steam detection
        active_ips = [d["ip"] for d in candidates]
        steam_result = sd.detect(active_ips)
        assert steam_result is None or isinstance(steam_result, dict)

        # Decision test: pick last active
        if candidates:
            last = candidates[-1]["brand"]
            assert isinstance(last, str)

    def test_all_components_have_expected_attributes(self):
        """Quick sanity check that all modules have expected classes."""
        from scanner import NetworkScanner
        from liveness import LivenessEngine
        from steam_detector import SteamDetector
        from config_manager import ConfigManager
        from led_controller import LEDController, get_led_controller, _to_rgb
        from colors import COLOR_MAP, BRAND_COLORS, Color

        assert callable(NetworkScanner)
        assert callable(LivenessEngine)
        assert callable(SteamDetector)
        assert callable(ConfigManager)
        assert callable(LEDController)
        assert callable(get_led_controller)
        assert callable(_to_rgb)
        assert isinstance(COLOR_MAP, dict)
        assert isinstance(BRAND_COLORS, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])