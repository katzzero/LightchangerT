"""Tests for config_manager.py — ConfigManager singleton."""
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'python'))

from config_manager import ConfigManager, get_config_manager


SAMPLE_CONFIG = {
    "network": {"subnet": "192.168.1.0/24", "scan_interval_seconds": 30},
    "devices": {
        "static_list": [{"ip": "192.168.1.10", "mac": "00:11:22:33:44:55", "brand": "sony"}],
        "oui_prefixes": {"sony": ["00:04:1F"]},
    },
    "colors": {"sony": "blue", "default": "white"},
}


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(SAMPLE_CONFIG))
    return str(path)


@pytest.fixture(autouse=True)
def reset_singleton():
    ConfigManager._instance = None


class TestSingleton:
    def test_returns_same_instance(self):
        cm1 = ConfigManager()
        cm2 = ConfigManager()
        assert cm1 is cm2

    def test_get_config_manager_singleton(self):
        assert get_config_manager() is get_config_manager()

    def test_singleton_consistency(self):
        assert ConfigManager() is get_config_manager()


class TestLoad:
    def test_load_returns_config(self, config_file):
        cm = ConfigManager()
        config = cm.load(config_file)
        assert config["network"]["subnet"] == "192.168.1.0/24"
        assert config["devices"]["static_list"][0]["brand"] == "sony"

    def test_load_missing_file_raises(self):
        cm = ConfigManager()
        with pytest.raises(FileNotFoundError):
            cm.load("/tmp/nonexistent_config_xyz.json")

    def test_load_invalid_json_raises(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{invalid json}")
        cm = ConfigManager()
        with pytest.raises(json.JSONDecodeError):
            cm.load(str(path))

    def test_reload_returns_fresh_config(self, config_file):
        cm = ConfigManager()
        cm.load(config_file)

        with open(config_file, "w") as f:
            json.dump({"network": {"subnet": "10.0.0.0/8"}}, f)

        refreshed = cm.reload()
        assert refreshed["network"]["subnet"] == "10.0.0.0/8"


class TestGet:
    def test_full_config(self, config_file):
        cm = ConfigManager()
        cm.load(config_file)
        assert cm.get()["network"]["subnet"] == "192.168.1.0/24"

    def test_top_level_key(self, config_file):
        cm = ConfigManager()
        cm.load(config_file)
        assert cm.get("network")["subnet"] == "192.168.1.0/24"

    def test_nested_key(self, config_file):
        cm = ConfigManager()
        cm.load(config_file)
        assert cm.get("network.scan_interval_seconds") == 30

    def test_missing_key_returns_default(self, config_file):
        cm = ConfigManager()
        cm.load(config_file)
        assert cm.get("nonexistent.key", "fallback") == "fallback"

    def test_missing_key_no_default(self, config_file):
        cm = ConfigManager()
        cm.load(config_file)
        assert cm.get("nonexistent") is None


class TestUpdate:
    def test_modifies_in_memory_config(self, config_file):
        cm = ConfigManager()
        cm.load(config_file)
        cm.update({"network": {"scan_interval_seconds": 60}})
        assert cm.get("network.scan_interval_seconds") == 60

    def test_persists_to_file(self, config_file):
        cm = ConfigManager()
        cm.load(config_file)
        cm.update({"network": {"scan_interval_seconds": 120}})

        with open(config_file) as f:
            saved = json.load(f)
        assert saved["network"]["scan_interval_seconds"] == 120

    def test_deep_nested(self, config_file):
        cm = ConfigManager()
        cm.load(config_file)
        cm.update({"devices": {"static_list": []}})
        assert cm.get("devices.static_list") == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
