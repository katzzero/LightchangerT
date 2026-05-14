import hashlib
import hmac
import secrets
from abc import ABC, abstractmethod
import logging

from colors import COLOR_MAP, Color

logger = logging.getLogger(__name__)

COLOR_MAP_LEGACY = COLOR_MAP  # Backward compatibility alias


class LEDController(ABC):
    @abstractmethod
    def set_color(self, color_name):
        """Sets the LED strip to a specific color."""
        pass

    @abstractmethod
    def off(self):
        """Turns off the LED strip."""
        pass

    @staticmethod
    def _to_rgb(color_name):
        """Convert color name to RGB tuple.

        Accepts:
        - Named colors ("blue", "red", etc.)
        - Hex strings ("#FF5500" or "FF5500")
        - RGB tuples (255, 0, 0)

        Falls back to white for unknown names.
        """
        if isinstance(color_name, tuple):
            return color_name
        color_name = str(color_name).lower().strip()
        if color_name in COLOR_MAP:
            return COLOR_MAP[color_name]

        if color_name.startswith("#"):
            color_name = color_name[1:]
        if len(color_name) == 6:
            try:
                return tuple(int(color_name[i:i+2], 16) for i in (0, 2, 4))
            except ValueError:
                pass

        logger.warning(f"Unknown color '{color_name}', defaulting to white")
        return COLOR_MAP["white"]


class FastLEDController(LEDController):
    def __init__(self, config):
        self.pin = config['hardware']['led_pin']
        self.num_leds = config['hardware']['num_leds']
        self.brightness = config['hardware'].get('brightness', 128)
        self.strip = [0] * self.num_leds
        self.fastled = None

        try:
            from FastLED import FastLED
            self.fastled = FastLED(self.pin, self.num_leds, data_format='GRB')
            logger.info(f"FastLED initialized on pin {self.pin} with {self.num_leds} LEDs")
        except ImportError:
            logger.error("FastLED library not installed. Run: pip install py-FastLED")

    def set_color(self, color_name):
        rgb = self._to_rgb(color_name)
        for i in range(self.num_leds):
            self.strip[i] = (rgb[0], rgb[1], rgb[2])
        if self.fastled:
            self.fastled.setBrightness(self.brightness)
            self.fastled.setPixels(self.strip)
            self.fastled.show()

    def off(self):
        if self.strip:
            self.strip = [0] * self.num_leds
        if self.fastled:
            self.fastled.setBrightness(0)
            self.fastled.setPixels([0] * self.num_leds)
            self.fastled.show()
            self.fastled.setBrightness(self.brightness)


class NeoPixelController(LEDController):
    def __init__(self, config):
        self.pin = config['hardware']['led_pin']
        self.num_leds = config['hardware']['num_leds']
        self.brightness = config['hardware'].get('brightness', 1.0)
        self._neopixel_available = False
        self.neopixels = None

        try:
            import neopixel
            self.neopixels = neopixel.NeoPixel(self.pin, self.num_leds, brightness=self.brightness, auto_write=False)
            self._neopixel_available = True
            logger.info(f"NeoPixel initialized on pin {self.pin} with {self.num_leds} LEDs")
        except ImportError:
            logger.error("NeoPixel library not installed. Run: pip install adafruit-circuitpython-neopixel")

    def set_color(self, color_name):
        rgb = self._to_rgb(color_name)
        if self.neopixels:
            for i in range(self.num_leds):
                self.neopixels[i] = rgb
            self.neopixels.brightness = self.brightness
            self.neopixels.show()

    def off(self):
        if self.neopixels:
            for i in range(self.num_leds):
                self.neopixels[i] = (0, 0, 0)
            self.neopixels.show()


class RPiLEDController(LEDController):
    def __init__(self, config):
        self.pin = config['hardware']['led_pin']
        self.num_leds = config['hardware']['num_leds']
        self.brightness = config['hardware'].get('brightness', 200)
        self._rpi_available = False
        self.strip = None
        self.PWM = None

        try:
            import rpi_ws281x
            self.PWM = rpi_ws281x
            self.strip = self.PWM.Strip(self.num_leds, self.pin, 800000, 7, False, 255, self.brightness, rpi_ws281x.GRB)
            self.strip.begin()
            self._rpi_available = True
            logger.info(f"RPi_WS281X initialized on pin {self.pin} with {self.num_leds} LEDs")
        except ImportError:
            logger.error("rpi_ws281x library not installed. Run: pip install rpi_ws281x (Raspberry Pi only)")

    def set_color(self, color_name):
        rgb = self._to_rgb(color_name)
        if self.strip:
            for i in range(self.num_leds):
                self.strip.setPixelColor(i, self.PWM.Color(rgb[0], rgb[1], rgb[2]))
            self.strip.show()

    def off(self):
        if self.strip:
            for i in range(self.num_leds):
                self.strip.setPixelColor(i, 0)
            self.strip.show()


def _to_rgb(color_name):
    """Convert a color name, hex string, or tuple to an RGB tuple."""
    return LEDController._to_rgb(color_name)


def get_led_controller(config):
    lib = config['hardware']['led_library'].upper()
    if lib == "FASTLED":
        return FastLEDController(config)
    elif lib == "NEOPIXEL":
        return NeoPixelController(config)
    elif lib in ("RPI_WS281X", "RPI_WS2812", "WS281X"):
        return RPiLEDController(config)
    else:
        raise ValueError(f"Unsupported LED library: {lib}")