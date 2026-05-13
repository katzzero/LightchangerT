import pytest
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from liveness import LivenessEngine


class TestLivenessIntegration:
    """Integration tests for liveness.py."""

    def test_is_alive_with_config(self):
        """LivenessEngine works when initialized with config."""
        config = {"network": {"subnet": "192.168.1.0/24"}}
        engine = LivenessEngine.__new__(LivenessEngine)
        engine.config = config
        # Should not crash
        result = engine.is_alive("127.0.0.1")
        assert isinstance(result, bool)

    def test_multiple_pings(self):
        """Multiple calls to is_alive don't interfere."""
        engine = LivenessEngine.__new__(LivenessEngine)
        r1 = engine.is_alive("127.0.0.1")
        r2 = engine.is_alive("127.0.0.1")
        assert isinstance(r1, bool)
        assert isinstance(r2, bool)

    def test_handles_none_config(self):
        """Engine with no config doesn't crash on is_alive."""
        engine = LivenessEngine.__new__(LivenessEngine)
        engine.config = {}
        result = engine.is_alive("127.0.0.1")
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])