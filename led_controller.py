from abc import ABC, abstractmethod
import json

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
        print(f"FastLED initialized on pin {self.pin} with {self.num_leds} LEDs")

    def set_color(self, color_name):
        print(f"FastLED: Setting color to {color_name}")

    def off(self):
        print("FastLED: Turning OFF")

class NeoPixelController(LEDController):
    def __init__(self, config):
        self.pin = config['hardware']['led_pin']
        print(f"NeoPixel initialized on pin {self.pin}")

    def set_color(self, color_name):
        print(f"NeoPixel: Setting color to {color_name}")

    def off(self):
        print("NeoPixel: Turning OFF")

class RPiLEDController(LEDController):
    def __init__(self, config):
        self.pin = config['hardware']['led_pin']
        print(f"RPi_WS281X initialized on pin {self.pin}")

    def set_color(self, color_name):
        print(f"RPi_WS281X: Setting color to {color_name}")

    def off(self):
        print("RPi_WS281X: Turning OFF")

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
