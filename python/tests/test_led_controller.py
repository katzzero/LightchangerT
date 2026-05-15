"""Tests for led_controller.py — LED drivers and color conversion."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'python'))

from led_controller import (
    LEDController, Color, FastLEDController,
    NeoPixelController, RPiLEDController, TuyaLEDController,
    COLOR_MAP, get_led_controller
)


class TestColorMap:
    def test_contains_all_basics(self):
        for color in ["black", "white", "red", "green", "blue"]:
            assert color in COLOR_MAP

    def test_contains_gaming_colors(self):
        for color in ["light_blue", "light_green"]:
            assert color in COLOR_MAP

    def test_white_is_rgb(self):
        assert COLOR_MAP["white"] == (255, 255, 255)

    def test_black_is_rgb(self):
        assert COLOR_MAP["black"] == (0, 0, 0)

    def test_blue_is_rgb(self):
        assert COLOR_MAP["blue"] == (0, 0, 255)


class TestToRGB:
    def test_named_color(self):
        result = LEDController._to_rgb("white")
        assert result == (255, 255, 255)

    def test_named_light_blue(self):
        result = LEDController._to_rgb("light_blue")
        assert result == (0, 191, 255)

    def test_rgb_tuple_passthrough(self):
        result = LEDController._to_rgb((255, 100, 50))
        assert result == (255, 100, 50)

    def test_hex_color(self):
        result = LEDController._to_rgb("#FF5500")
        assert result == (255, 85, 0)

    def test_hex_no_hash(self):
        result = LEDController._to_rgb("FF5500")
        assert result == (255, 85, 0)

    def test_unknown_defaults_to_white(self, caplog):
        result = LEDController._to_rgb("hot_pink")
        assert result == COLOR_MAP["white"]
        assert "Unknown color" in caplog.text

    def test_lowercase_handling(self):
        result_upper = LEDController._to_rgb("BLUE")
        result_lower = LEDController._to_rgb("blue")
        assert result_upper == result_lower


# ---- Mock controller for tests that don't need hardware ----
class MockLEDController(LEDController):
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


class TestMockLED:
    def test_mock_sets_color(self, mock_led):
        mock_led.set_color("blue")
        assert mock_led.last_color == "blue"

    def test_mock_off(self, mock_led):
        mock_led.off()
        assert mock_led.off_called is True


class TestFastLEDController:
    @pytest.fixture
    def sample_config(self):
        return {
            "hardware": {
                "led_pin": 13,
                "num_leds": 30,
                "brightness": 128,
                "led_library": "FASTLED"
            }
        }

    def test_init_saves_config(self, sample_config):
        controller = FastLEDController(sample_config)
        assert controller.pin == 13
        assert controller.num_leds == 30
        assert controller.brightness == 128

    def test_init_creates_strip(self, sample_config):
        controller = FastLEDController(sample_config)
        assert controller.strip == [0] * 30

    def test_set_color_without_library(self, sample_config):
        controller = FastLEDController(sample_config)
        controller.set_color("blue")
        assert controller.strip[0] == (0, 0, 255)


class TestNeoPixelController:
    def test_init_saves_config(self):
        config = {
            "hardware": {
                "led_pin": 6,
                "num_leds": 60,
                "brightness": 0.5,
                "led_library": "NEOPIXEL"
            }
        }
        controller = NeoPixelController(config)
        assert controller.pin == 6
        assert controller._neopixel_available is False


class TestRPiLEDController:
    def test_init_saves_config(self):
        config = {
            "hardware": {
                "led_pin": 18,
                "num_leds": 50,
                "brightness": 200,
                "led_library": "RPI_WS281X"
            }
        }
        controller = RPiLEDController(config)
        assert controller.pin == 18
        assert controller._rpi_available is False


class TestTuyaLEDController:
    def test_init_reads_tuya_config(self):
        config = {
            "hardware": {
                "led_library": "TUYA",
                "brightness": 80,
                "tuya": {
                    "device_id": "abc123",
                    "address": "192.168.1.50",
                    "local_key": "key456",
                    "version": 3.3
                }
            }
        }
        controller = TuyaLEDController(config)
        assert controller.device_id == "abc123"
        assert controller.address == "192.168.1.50"
        assert controller.local_key == "key456"
        assert controller.version == 3.3
        assert controller.brightness == 80
        # tinytuya not installed in test env
        assert controller._device is None

    def test_init_defaults_version(self):
        config = {
            "hardware": {
                "led_library": "TUYA",
                "tuya": {
                    "device_id": "abc",
                    "address": "1.2.3.4",
                    "local_key": "key"
                }
            }
        }
        controller = TuyaLEDController(config)
        assert controller.version == 3.3

    def test_init_handles_missing_tuya_section(self):
        config = {"hardware": {"led_library": "TUYA"}}
        controller = TuyaLEDController(config)
        assert controller.device_id == ""
        assert controller.address == ""
        assert controller._device is None


class TestGetLEDController:
    @pytest.fixture
    def sample_config(self):
        return {
            "hardware": {
                "led_pin": 13,
                "num_leds": 30,
                "brightness": 128,
                "led_library": "FASTLED"
            }
        }

    def test_fastled(self, sample_config):
        controller = get_led_controller(sample_config)
        assert isinstance(controller, FastLEDController)

    def test_neopixel(self, sample_config):
        config = dict(sample_config)
        config["hardware"]["led_library"] = "NEOPIXEL"
        controller = get_led_controller(config)
        assert isinstance(controller, NeoPixelController)

    def test_rpi_ws281x(self, sample_config):
        config = dict(sample_config)
        config["hardware"]["led_library"] = "RPI_WS281X"
        controller = get_led_controller(config)
        assert isinstance(controller, RPiLEDController)

    def test_rpi_ws2812_alias(self, sample_config):
        config = dict(sample_config)
        config["hardware"]["led_library"] = "RPI_WS2812"
        controller = get_led_controller(config)
        assert isinstance(controller, RPiLEDController)

    def test_tuya(self, sample_config):
        config = dict(sample_config)
        config["hardware"]["led_library"] = "TUYA"
        config["hardware"]["tuya"] = {
            "device_id": "abc",
            "address": "1.2.3.4",
            "local_key": "key"
        }
        controller = get_led_controller(config)
        assert isinstance(controller, TuyaLEDController)

    def test_unsupported_library_raises(self, sample_config):
        config = dict(sample_config)
        config["hardware"]["led_library"] = "UNKNOWN_LIB"
        with pytest.raises(ValueError, match="Unsupported LED library"):
            get_led_controller(config)


class TestIntegration:
    @pytest.fixture
    def sample_config(self):
        return {
            "hardware": {
                "led_pin": 13,
                "num_leds": 30,
                "brightness": 128,
                "led_library": "FASTLED"
            }
        }

    def test_blue_color_applied_to_strip(self, sample_config):
        controller = FastLEDController(sample_config)
        controller.set_color("blue")
        expected = (0, 0, 255)
        for i in range(30):
            assert controller.strip[i] == expected

    def test_white_color_applied_to_strip(self, sample_config):
        controller = FastLEDController(sample_config)
        controller.set_color("white")
        expected = (255, 255, 255)
        for i in range(30):
            assert controller.strip[i] == expected

    def test_hex_color_applied(self, sample_config):
        controller = FastLEDController(sample_config)
        controller.set_color("#00FF00")
        expected = (0, 255, 0)
        for i in range(30):
            assert controller.strip[i] == expected

    def test_off_zeros_strip(self, sample_config):
        controller = FastLEDController(sample_config)
        controller.set_color("blue")
        controller.off()
        for i in range(30):
            assert controller.strip[i] == 0