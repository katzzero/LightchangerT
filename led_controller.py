from abc import ABC, abstractmethod
import json
import logging

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

class FastLEDController(LEDController):
    def __init__(self, config):
        self.pin = config['hardware']['led_pin']
        self.num_leds = config['hardware']['num_leds']
        logger.info(f"FastLED initialized on pin {self.pin} with {self.num_leds} LEDs")

    def set_color(self, color_name):
        logger.debug(f"FastLED: Setting color to {color_name}")

    def off(self):
        logger.debug("FastLED: Turning OFF")

class NeoPixelController(LEDController):
    def __init__(self, config):
        self.pin = config['hardware']['led_pin']
        logger.info(f"NeoPixel initialized on pin {self.pin}")

    def set_color(self, color_name):
        logger.debug(f"NeoPixel: Setting color to {color_name}")

    def off(self):
        logger.debug("NeoPixel: Turning OFF")

class RPiLEDController(LEDController):
    def __init__(self, config):
        self.pin = config['hardware']['led_pin']
        logger.info(f"RPi_WS281X initialized on pin {self.pin}")

    def set_color(self, color_name):
        logger.debug(f"RPi_WS281X: Setting color to {color_name}")

    def off(self):
        logger.debug("RPi_WS281X: Turning OFF")

def get_led_controller(config):
    lib = config['hardware']['led_library'].upper()
    if lib == "FASTLED":
        return FastLEDController(config)
    elif lib == "NEOPIXEL":
        return NeoPixelController(config)
    elif lib == "RPI_WS28X":
        return RPiLEDController(config)
    else:
        raise ValueError(f"Unsupported LED library: {lib}")

if __name__ == "__main__":
    with open("config.json", 'r') as f:
        conf = json.load(f)
    ctrl = get_led_controller(conf)
    ctrl.set_color("blue")
    ctrl.off()
