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

// Hardware Objects
LEDController led;
ConfigManager configManager;

// Web Server on Port 80
WebServer server(80);

// State
std::map<String, unsigned long> lastSeen;

void handleRoot() {
    server.send(200, "text/html", INDEX_HTML);
}

void handleSave() {
    if (server.hasArg("ip") && server.hasArg("brand")) {
        String ip = server.arg("ip");
        String brand = server.arg("brand");
        
        configManager.addDevice(ip, brand);
        
        server.send(200, "text/html", "<html><body><h1>Device Added! <a href='/'>Back</a></h1></body></html>");
    } else {
        server.send(400, "text/html", "Invalid Data");
    }
}

void handleClear() {
    configManager.clearDevices();
    server.send(200, "text/html", "<html><body><h1>Devices Cleared! <a href='/'>Back</a></h1></body></html>");
}

void setup() {
    Serial.begin(115200);

    // LED Init
    led.begin();

    // WiFi Init
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi Connected");
    Serial.println(WiFi.localIP());

    // Config Manager Init
    configManager.begin();

    // Web Server Routes
    server.on("/", handleRoot);
    server.on("/save", HTTP_POST, handleSave);
    server.on("/clear", HTTP_GET, handleClear);
    
    server.begin();
    Serial.println("Web Server started on port 80");
}

void loop() {
    server.handleClient();

    // Get configured devices
    std::vector<DeviceConfig> devices = configManager.getDevices();
    bool anyActive = false;
    String winnerBrand = "";
    unsigned long maxTs = 0;

    for (const auto& dev : devices) {
        IPAddress ip;
        if (ip.fromString(dev.ip)) {
            // Ping the device
            if (ESPPing.ping(ip, 1)) {
                lastSeen[dev.brand] = millis();
                anyActive = true;
                Serial.print("Device Online: ");
                Serial.println(dev.ip);

                if (lastSeen[dev.brand] > maxTs) {
                    maxTs = lastSeen[dev.brand];
                    winnerBrand = dev.brand;
                }
            }
        }
    }

    if (!anyActive) {
        led.setColor(COLOR_DEFAULT); // Default White
    } else {
        if (winnerBrand == "sony") led.setColor(COLOR_SONY);
        else if (winnerBrand == "microsoft") led.setColor(COLOR_MICROSOFT);
        else if (winnerBrand == "nintendo") led.setColor(COLOR_NINTENDO);
        else if (winnerBrand == "steam") led.setColor(COLOR_STEAM);
        else if (winnerBrand == "nvidia") led.setColor(COLOR_NVIDIA);
        else led.setColor(COLOR_DEFAULT);
    }

    delay(1000); // Check every second
}