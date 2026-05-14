// Stale legacy main.cpp — replaced by esp32.ino (Arduino framework)
// This file is kept only for reference. Do not compile.
// See esp32.ino for the current ESP32 entry point.

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <ESPPing.h>
#include <FastLED.h>

#include "config.h"
#include "led_controller.h"
#include "web_ui.h"
#include "config_manager.h"

LEDController led;
ConfigManager configManager;
WebServer server(80);
std::map<String, unsigned long> lastSeen;

void handleRoot() { server.send(200, "text/html", INDEX_HTML); }
void handleSave() { /* ... */ }
void setup() {
    Serial.begin(115200);
    led.begin();
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
    Serial.println("\nWiFi Connected");
    configManager.begin();
    server.on("/", handleRoot);
    server.on("/save", HTTP_POST, handleSave);
    server.begin();
}
void loop() {
    server.handleClient();
    delay(1000);
}