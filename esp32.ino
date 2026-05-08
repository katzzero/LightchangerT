#include <Arduino.h>
#include <map>
#include <WiFi.h>
#include <FastLED.h>
#include <ESPping.h>
#include <ESPmDNS.h>

#include "config.h"
#include "led_controller.h"
#include "network_scanner.h"
#include "liveness_engine.h"
#include "steam_detector.h"

LEDController led;
NetworkScanner scanner;
LivenessEngine liveness;
SteamDetector steam;

std::map<String, unsigned long> lastSeen;

void setup() {
    Serial.begin(115200);

    led.begin();

    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi Connected");

    if (!MDNS.begin("lightchanger-esp32")) {
        Serial.println("Error setting up MDNS responder!");
    }
}

void loop() {
    Serial.println("Scanning network...");

    std::vector<Device> candidates = scanner.scan();
    std::vector<IPAddress> activeIps;
    std::vector<String> currentlyActiveBrands;

    for (const auto& device : candidates) {
        if (liveness.isAlive(device.ip)) {
            lastSeen[device.brand] = millis();
            currentlyActiveBrands.push_back(device.brand);
            activeIps.push_back(device.ip);
        }
    }

    if (steam.detect(activeIps)) {
        lastSeen["steam"] = millis();
        currentlyActiveBrands.push_back("steam");
    }

    if (currentlyActiveBrands.empty()) {
        led.setColor(COLOR_DEFAULT);
    } else {
        String winner = "";
        unsigned long maxTs = 0;

        for (const auto& brand : currentlyActiveBrands) {
            if (lastSeen[brand] > maxTs) {
                maxTs = lastSeen[brand];
                winner = brand;
            }
        }

        if (winner == "sony") led.setColor(COLOR_SONY);
        else if (winner == "microsoft") led.setColor(COLOR_MICROSOFT);
        else if (winner == "nintendo") led.setColor(COLOR_NINTENDO);
        else if (winner == "steam") led.setColor(COLOR_STEAM);
        else if (winner == "nvidia") led.setColor(COLOR_NVIDIA);
        else led.setColor(COLOR_DEFAULT);
    }

    delay(SCAN_INTERVAL_MS);
}