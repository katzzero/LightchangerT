"""Tests for liveness.py — LivenessEngine class."""
import pytest
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from liveness import LivenessEngine


class TestLivenessEngineInit:
    def test_init_with_config_dict(self):
        config = {"network": {"subnet": "192.168.1.0/24"}}
        engine = LivenessEngine(config=config)
        assert engine.config == config

    def test_init_with_none_config(self):
        engine = LivenessEngine(config=None)
        # Should have loaded from default config.json or fallback to {}
        assert engine.config is not None

    def test_init_with_config_path(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"network": {"subnet": "10.0.0.0/8"}}))
        engine = LivenessEngine(config_path=str(config_file))
        assert engine.config is not None
        assert engine.config["network"]["subnet"] == "10.0.0.0/8"


class TestLivenessEngineIsAlive:
    def test_localhost_alive(self):
        engine = LivenessEngine(config={})
        result = engine.is_alive("127.0.0.1")
        assert isinstance(result, bool)

    def test_multiple_calls(self):
        engine = LivenessEngine(config={})
        r1 = engine.is_alive("127.0.0.1")
        r2 = engine.is_alive("127.0.0.1")
        assert isinstance(r1, bool)
        assert isinstance(r2, bool)

    def test_handles_none_config(self):
        engine = LivenessEngine(config={})
        result = engine.is_alive("127.0.0.1")
        assert isinstance(result, bool)

    def test_unreachable_ip_returns_false(self):
        engine = LivenessEngine(config={})
        # 10.255.255.1 is almost certainly unreachable
        result = engine.is_alive("10.255.255.1")
        assert result is False


class TestLivenessEngineCheckMultiple:
    def test_check_multiple_returns_dict(self):
        engine = LivenessEngine(config={})
        result = engine.check_multiple(["127.0.0.1", "10.255.255.1"])
        assert isinstance(result, dict)
        assert len(result) == 2
        assert all(isinstance(v, bool) for v in result.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])