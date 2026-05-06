#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

#include <FastLED.h>
#include "config.h"

class LEDController {
private:
    CRGB leds[NUM_LEDS];

public:
    void begin() {
        FastLED.addLEDS<WS2812B, LED_PIN, GRB>(leds, NUM_LEDS);
        FastLED.setBrightness(BRIGHTNESS);
        setBkgColor();
    }

    void setBkgColor() {
        fill_solid(leds, NUM_LEDS, CRGB(COLOR_DEFAULT.r, COLOR_DEFAULT.g, COLOR_DEFAULT.b));
        FastLED.show();
    }

    void setColor(Color color) {
        fill_solid(leds, NUM_LEDS, CRGB(color.r, color.g, color.b));
        FastLED.show();
    }

    void off() {
        fill_solid(leds, NUM_LEDS, CRGB::Black);
        FastLED.show();
    }
};

#endif