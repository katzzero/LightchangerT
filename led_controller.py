from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

# Color name to RGB mapping
COLOR_MAP = {
    "blue": (0, 0, 255),
    "green": (0, 255, 0),
    "red": (255, 0, 0),
    "light_blue": (0, 191, 255),
    "light_green": (144, 238, 144),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}


class LEDController(ABC):
    @abstractmethod
    def set_color(self, color_name):
        """Sets the LED strip to a specific color."""
        pass

    @abstractmethod
    def off(self):
        """Turns off the LED strip."""
        pass

    def _to_rgb(self, color_name):
        """Convert color name to RGB tuple."""
        if isinstance(color_name, tuple):
            return color_name
        color_name = color_name.lower().strip()
        if color_name in COLOR_MAP:
            return COLOR_MAP[color_name]

        # Try parsing as hex (#RRGGBB or RRGGBB)
        if isinstance(color_name, str):
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

        try:
            from FastLED import FastLED
            self.fastled = FastLED(self.pin, self.num_leds, data_format='GRB')
            self.strip = [0] * self.num_leds
            logger.info(f"FastLED initialized on pin {self.pin} with {self.num_leds} LEDs")
        except ImportError:
            logger.error("FastLED library not installed. Run: pip install py-FastLED")
            self.fastled = None
            self.strip = []

    def set_color(self, color_name):
        rgb = self._to_rgb(color_name)
        for i in range(self.num_leds):
            self.strip[i] = (rgb[0], rgb[1], rgb[2])
        if self.fastled:
            self.fastled.setBrightness(self.brightness)
            self.fastled.setPixels(self.strip)
            self.fastled.show()

    def off(self):
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

        try:
            import neopixel
            self.neopixels = neopixel.NeoPixel(self.pin, self.num_leds, brightness=self.brightness, auto_write=False)
            logger.info(f"NeoPixel initialized on pin {self.pin} with {self.num_leds} LEDs")
        except ImportError:
            logger.error("NeoPixel library not installed. Run: pip install adafruit-circuitpython-neopixel")
            self.neopixels = None

    def set_color(self, color_name):
        rgb = self._to_rgb(color_name)
        for i in range(self.num_leds):
            self.neopixels[i] = rgb
        if self.neopixels:
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

        try:
            import rpi_ws281x
            self.PWM = rpi_ws281x
            self.strip = self.PWM.Strip(self.num_leds, self.pin, 800000, 7, False, 255, self.brightness, rpi_ws281x.GRB)
            self.strip.begin()
            logger.info(f"RPi_WS281X initialized on pin {self.pin} with {self.num_leds} LEDs")
        except ImportError:
            logger.error("rpi_ws281x library not installed. Run: pip install rpi_ws281x (Raspberry Pi only)")
            self.strip = None

    def set_color(self, color_name):
        rgb = self._to_rgb(color_name)
        for i in range(self.num_leds):
            self.strip.setPixelColor(i, self.PWM.Color(rgb[0], rgb[1], rgb[2]))
        if self.strip:
            self.strip.show()

    def off(self):
        if self.strip:
            for i in range(self.num_leds):
                self.strip.setPixelColor(i, 0)
            self.strip.show()


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


if __name__ == "__main__":
    import json
    with open("config.json", 'r') as f:
        conf = json.load(f)
    ctrl = get_led_controller(conf)
    ctrl.set_color("blue")
    ctrl.off()
