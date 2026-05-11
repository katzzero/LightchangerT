import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from led_controller import (
    LEDController, Color, FastLEDController,
    NeoPixelController, RPiLEDController,
    COLOR_MAP, get_led_controller
)


class TestColorMap:
    """Tests for the COLOR_MAP constant."""

    def test_contains_all_basics(self):
        for color in ["blue", "green", "red", "white", "black"]:
            assert color in COLOR_MAP, f"Missing basic color: {color}"

    def test_contains_gaming_colors(self):
        for color in ["light_blue", "light_green"]:
            assert color in COLOR_MAP, f"Missing gaming color: {color}"

    def test_white_is_rgb(self):
        assert COLOR_MAP["white"] == (255, 255, 255)

    def test_black_is_rgb(self):
        assert COLOR_MAP["black"] == (0, 0, 0)

    def test_blue_is_rgb(self):
        assert COLOR_MAP["blue"] == (0, 0, 255)


class TestMockLED:
    """Basic test to verify the testing fixture works."""

    def test_mock_sets_color(self, mock_led):
        mock_led.set_color("blue")
        assert mock_led.last_color == "blue"

    def test_mock_off(self, mock_led):
        mock_led.off()
        assert mock_led.off_called is True


class TestToRGB:
    """Tests for the _to_rgb method on base class."""

    def test_named_color(self):
        result = LEDController._to_rgb(None, "white")
        assert result == (255, 255, 255)

    def test_named_light_blue(self):
        result = LEDController._to_rgb(None, "light_blue")
        assert result == (0, 191, 255)

    def test_rgb_tuple_passthrough(self):
        result = LEDController._to_rgb(None, (255, 100, 50))
        assert result == (255, 100, 50)

    def test_hex_color(self):
        result = LEDController._to_rgb(None, "#FF5500")
        assert result == (255, 85, 0)

    def test_hex_no_hash(self):
        result = LEDController._to_rgb(None, "FF5500")
        assert result == (255, 85, 0)

    def test_unknown_defaults_to_white(self, caplog):
        with caplog.at_level("WARNING"):
            result = LEDController._to_rgb(None, "hot_pink")
        assert result == COLOR_MAP["white"]
        assert "Unknown color" in caplog.text


class TestFastLEDController:
    """Tests for FastLED controller."""

    def test_init_saves_config(self, sample_config):
        controller = FastLEDController(sample_config)
        assert controller.pin == 13
        assert controller.num_leds == 30
        assert controller.brightness == 128

    def test_init_without_library_logs_error(self, sample_config, caplog):
        with caplog.at_level("ERROR"):
            FastLEDController(sample_config)
        assert "FastLED library not installed" in caplog.text

    def test_init_creates_strip(self, sample_config):
        controller = FastLEDController(sample_config)
        assert controller.strip == [0] * 30

    def test_set_color_without_library(self, sample_config):
        controller = FastLEDController(sample_config)
        controller.set_color("blue")
        # strip should be set even without library
        assert controller.strip[0] == (0, 0, 255)


class TestNeoPixelController:
    """Tests for NeoPixel controller."""

    def test_init_saves_config(self, sample_config):
        config = dict(sample_config)
        config["hardware"]["led_library"] = "NEOPIXEL"
        with pytest.raises(ImportError):
            NeoPixelController(config)


class TestRPiLEDController:
    """Tests for RPi WS281X controller."""

    def test_init_saves_config(self, sample_config):
        config = dict(sample_config)
        config["hardware"]["led_library"] = "RPI_WS281X"
        with pytest.raises(ImportError):
            RPiLEDController(config)


class TestGetLEDController:
    """Tests for the factory function get_led_controller."""

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

    def test_unsupported_library_raises(self, sample_config):
        config = dict(sample_config)
        config["hardware"]["led_library"] = "UNKNOWN_LIB"
        with pytest.raises(ValueError, match="Unsupported LED library"):
            get_led_controller(config)


class TestIntegration:
    """Integration-like tests that check color mapping end-to-end."""

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
