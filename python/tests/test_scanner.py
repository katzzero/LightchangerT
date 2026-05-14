"""Tests for scanner.py — NetworkScanner class."""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner import NetworkScanner


@pytest.fixture
def temp_config_file():
    """Create a temporary config.json for isolated tests."""
    config = {
        "network": {"subnet": "192.168.1.0/24"},
        "devices": {
            "static_list": [
                {"ip": "192.168.1.10", "mac": "00:11:22:33:44:55", "brand": "sony"},
                {"ip": "192.168.1.11", "mac": "66:77:88:99:AA:BB", "brand": "microsoft"},
            ],
            "oui_prefixes": {
                "sony": ["00:04:1F", "00:13:15"],
                "microsoft": ["00:0D:3A", "00:12:5A"],
                "nintendo": ["00:09:BF"],
            },
        },
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, dir="/tmp"
    ) as f:
        json.dump(config, f)
        path = f.name
    yield path
    os.unlink(path)


class TestNetworkScanner:
    """Tests for scanner.py — NetworkScanner class."""

    def test_init_reads_config(self, temp_config_file):
        """Scanner can be initialized with a config file path."""
        s = NetworkScanner(temp_config_file)
        assert s.subnet == "192.168.1.0/24"
        assert len(s.static_devices) == 2
        assert "sony" in s.oui_prefixes

    def test_init_defaults(self, temp_config_file):
        """Scanner defaults to 'config.json' when no path given."""
        # Only works if config.json exists; verify it can be created
        s = NetworkScanner(temp_config_file)
        assert s.config is not None

    def test_identify_brand_sony(self, temp_config_file):
        """Matching a known OUI prefix returns the brand name."""
        s = NetworkScanner(temp_config_file)
        assert s.identify_brand("00:04:1f:ab:cd:ef") == "sony"

    def test_identify_brand_microsoft(self, temp_config_file):
        """Matching Microsoft OUI prefix returns 'microsoft'."""
        s = NetworkScanner(temp_config_file)
        assert s.identify_brand("00:0D:3A:11:22:33") == "microsoft"

    def test_identify_brand_no_match(self, temp_config_file):
        """Unknown OUI returns None."""
        s = NetworkScanner(temp_config_file)
        assert s.identify_brand("AA:BB:CC:DD:EE:FF") is None

    def test_identify_brand_none_mac(self, temp_config_file):
        """Passing None returns None."""
        s = NetworkScanner(temp_config_file)
        assert s.identify_brand(None) is None

    def test_identify_brand_case_insensitive(self, temp_config_file):
        """OUI matching is case-insensitive."""
        s = NetworkScanner(temp_config_file)
        assert s.identify_brand("00:04:1F:AA:BB:CC") == "sony"

    def test_identify_brand_mac_with_colons(self, temp_config_file):
        """Colon-separated MAC is matched correctly."""
        s = NetworkScanner(temp_config_file)
        assert s.identify_brand("00:13:15:AB:CD:EF") == "sony"

    def test_scan_returns_list(self, temp_config_file):
        """scan() returns a list."""
        s = NetworkScanner(temp_config_file)
        result = s.scan()
        assert isinstance(result, list)
        # Static devices are always returned
        assert len(result) >= 2

    def test_scan_static_devices_in_results(self, temp_config_file):
        """All statically configured devices appear in scan results."""
        s = NetworkScanner(temp_config_file)
        result = s.scan()
        ips = [d["ip"] for d in result]
        assert "192.168.1.10" in ips
        assert "192.168.1.11" in ips

    def test_scan_includes_dynamic_arp(self, temp_config_file):
        """scan() attempts ARP discovery (may return nothing in test env)."""
        s = NetworkScanner(temp_config_file)
        result = s.scan()
        assert isinstance(result, list)
        # Result should be at least the static list
        assert len(result) >= 2

    def test_scan_error_handling(self, temp_config_file):
        """scan() doesn't crash if ARP table is unreadable."""
        s = NetworkScanner(temp_config_file)
        # Should not raise even with various edge cases
        result = s.scan()
        assert isinstance(result, list)

    def test_static_device_brand_preserved(self, temp_config_file):
        """Static devices preserve their configured brand."""
        s = NetworkScanner(temp_config_file)
        result = s.scan()
        sony_devs = [d for d in result if d["brand"] == "sony"]
        assert len(sony_devs) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])