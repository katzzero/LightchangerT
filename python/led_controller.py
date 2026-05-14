from abc import ABC, abstractmethod
import logging

from colors import COLOR_MAP, Color

logger = logging.getLogger(__name__)


class LEDController(ABC):
    @abstractmethod
    def set_color(self, color_name):
        """Sets the LED strip to a specific color."""
        pass

    @abstractmethod
    def off(self):
        """Turns off the LED strip."""
        pass

    def _to_rgb(self, color):
        """Converts a color name, hex string, or RGB tuple to an (R, G, B) tuple."""
        if isinstance(color, tuple) and len(color) == 3:
            return color

        if isinstance(color, str):
            # Hex format: #RRGGBB or RRGGBB
            if color.startswith('#'):
                color = color[1:]
            if len(color) == 6 and all(c in '0123456789ABCDEFabcdef' for c in color):
                return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16))

            # Named color lookup
            if color in COLOR_MAP:
                return COLOR_MAP[color]

        logger.warning(f"Unknown color format: {color}, defaulting to white")
        return COLOR_MAP["white"]


class FastLEDController(LEDController):
    def __init__(self, config):
        self.pin = config['hardware']['led_pin']
        self.num_leds = config['hardware']['num_leds']
        self.brightness = config['hardware'].get('brightness', 255)
        self.strip = [0] * self.num_leds

        try:
            import FastLED  # noqa: F401
            self._fastled_available = True
            logger.info(f"FastLED initialized on pin {self.pin} with {self.num_leds} LEDs")
        except ImportError:
            self._fastled_available = False
            logger.error("FastLED library not installed - running in simulated mode")

    def set_color(self, color_name):
        rgb = self._to_rgb(color_name)
        logger.debug(f"FastLED: Setting color to {color_name} -> {rgb}")
        self.strip = [rgb] * self.num_leds
        if self._fastled_available:
            # Real FastLED hardware control would go here
            pass

    def off(self):
        logger.debug("FastLED: Turning OFF")
        self.strip = [0] * self.num_leds
        if self._fastled_available:
            pass


class NeoPixelController(LEDController):
    def __init__(self, config):
        self.pin = config['hardware']['led_pin']
        self.num_leds = config['hardware']['num_leds']
        self._neopixel_available = False

        try:
            import neopixel  # noqa: F401
            self._neopixel_available = True
            logger.info(f"NeoPixel initialized on pin {self.pin}")
        except ImportError:
            logger.error("neopixel library not installed - running in simulated mode")

    def set_color(self, color_name):
        rgb = self._to_rgb(color_name)
        logger.debug(f"NeoPixel: Setting color to {color_name} -> {rgb}")
        if self._neopixel_available:
            pass

    def off(self):
        logger.debug("NeoPixel: Turning OFF")
        if self._neopixel_available:
            pass


class RPiLEDController(LEDController):
    def __init__(self, config):
        self.pin = config['hardware']['led_pin']
        self.num_leds = config['hardware']['num_leds']
        self._rpi_available = False

        try:
            import rpi_ws281x  # noqa: F401
            self._rpi_available = True
            logger.info(f"RPi_WS281X initialized on pin {self.pin}")
        except ImportError:
            logger.error("rpi_ws281x library not installed - running in simulated mode")

    def set_color(self, color_name):
        rgb = self._to_rgb(color_name)
        logger.debug(f"RPi_WS281X: Setting color to {color_name} -> {rgb}")
        if self._rpi_available:
            pass

    def off(self):
        logger.debug("RPi_WS281X: Turning OFF")
        if self._rpi_available:
            pass


def get_led_controller(config):
    lib = config['hardware']['led_library'].upper()
    if lib == "FASTLED":
        return FastLEDController(config)
    elif lib == "NEOPIXEL":
        return NeoPixelController(config)
    elif lib in ("RPI_WS28X", "RPI_WS281X", "RPI_WS2812"):
        return RPiLEDController(config)
    else:
        raise ValueError(f"Unsupported LED library: {lib}")


def _to_rgb(color):
    """Module-level convenience function matching LEDController._to_rgb behavior."""
    return LEDController._to_rgb(None, color)


if __name__ == "__main__":
    import json
    with open("config.json", 'r') as f:
        conf = json.load(f)
    ctrl = get_led_controller(conf)
    ctrl.set_color("blue")
    ctrl.off()