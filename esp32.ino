#include <Arduino.h>
#include <map>
#include <vector>
#include <string>
#include <WiFi.h>
#include <WebServer.h>
#include <FastLED.h>
#include <ESPping.h>
#include <ESPmDNS.h>
#include <WiFiClient.h>

#include "config.h"
#include "led_controller.h"
#include "config_manager.h"
#include "liveness_engine.h"
#include "steam_detector.h"
#include "network_scanner.h"
#include "web_ui.h"

LEDController led;
ConfigManager configManager;
LivenessEngine liveness;
SteamDetector steam;

WebServer server(80);
WiFiServer commandServer(COMMAND_PORT_DEFAULT);

std::map<String, unsigned long> lastSeen;

unsigned long lastScanTime = 0;
const unsigned long scanInterval = SCAN_INTERVAL_MS;

bool wifiConnected = false;
bool wifiReconnecting = false;
unsigned long wifiReconnectStart = 0;
const unsigned long WIFI_RECONNECT_INTERVAL = 5000;

Color getColorForBrand(String brand) {
    for (int i = 0; i < NUM_BRAND_COLORS; i++) {
        if (brand.equalsIgnoreCase(String(BRAND_NAMES[i]))) {
            return BRAND_COLORS[i];
        }
    }
    return COLOR_DEFAULT;
}

void handleWiFiDisconnect() {
    if (WiFi.status() != WL_CONNECTED) {
        if (!wifiReconnecting) {
            Serial.println("WiFi disconnected. Reconnecting...");
            WiFi.disconnect(false);
            wifiReconnectStart = millis();
            wifiReconnecting = true;
        }
        if (millis() - wifiReconnectStart >= WIFI_RECONNECT_INTERVAL) {
            WiFi.begin(WIFI_SSID, WIFI_PASS);
            wifiReconnectStart = millis();
        }
    } else {
        wifiReconnecting = false;
    }
}

// Process a single command and return response string
String handleCommand(String cmd) {
    cmd.trim();

    if (cmd.startsWith("COLOR:")) {
        String colorName = cmd.substring(6);
        Color c = getColorForBrand(colorName);
        led.setColor(c);
        return "OK";
    }

    if (cmd.startsWith("RGB:")) {
        String rgb = cmd.substring(4);
        int parts[3];
        int count = sscanf(rgb.c_str(), "%d,%d,%d", &parts[0], &parts[1], &parts[2]);
        if (count == 3) {
            Color c = {
                (uint8_t)constrain(parts[0], 0, 255),
                (uint8_t)constrain(parts[1], 0, 255),
                (uint8_t)constrain(parts[2], 0, 255)
            };
            led.setColor(c);
            return "OK";
        }
        return "ERR:INVALID_RGB";
    }

    if (cmd == "OFF") {
        led.off();
        return "OK";
    }

    if (cmd == "STATUS?") {
        return "STATUS:active";
    }

    return "ERR:UNKNOWN";
}

// Handle one-shot TCP client connection (non-blocking)
void handleCommandClient(WiFiClient client) {
    String line = "";
    unsigned long timeout = millis();

    while (client.connected() && (millis() - timeout) < 5000) {
        if (client.available()) {
            timeout = millis();
            char c = client.read();
            if (c == '\n') {
                if (line.length() > 0) {
                    String response = handleCommand(line);
                    client.println(response);
                    line = "";
                }
            } else if (c != '\r') {
                line += c;
            }
        }
        yield();
    }
    client.stop();
}

void setup() {
    Serial.begin(115200);
    led.begin();

    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    wifiConnected = true;
    Serial.println("\nWiFi Connected");
    Serial.println(WiFi.localIP());
    lastScanTime = millis();

    configManager.begin();

    // Load command port from NVS (default COMMAND_PORT_DEFAULT)
    uint16_t cmdPort = configManager.getCommandPort();
    commandServer = WiFiServer(cmdPort);

    if (!MDNS.begin("lightchanger-esp32")) {
        Serial.println("Error setting up MDNS responder!");
    }

    // Web UI endpoints
    server.on("/", HTTP_GET, []() {
        server.send(200, "text/html", INDEX_HTML);
    });

    server.on("/save", HTTP_POST, [&]() {
        if (server.hasArg("ip") && server.hasArg("brand")) {
            String editMode = server.arg("edit_mode");
            String editIdxStr = server.arg("edit_idx");

            if (editMode == "1" && editIdxStr.length() > 0) {
                int editIdx = editIdxStr.toInt();
                std::vector<DeviceConfig> devices = configManager.getDevices();
                if (editIdx < (int)devices.size()) {
                    devices[editIdx].ip = server.arg("ip");
                    devices[editIdx].brand = server.arg("brand");
                    configManager.saveDevices(devices);
                    server.send(200, "text/html", "<html><body><h1>Device Updated! <a href='/'>Back</a></h1></body></html>");
                } else {
                    server.send(400, "text/html", "Invalid Index");
                }
            } else {
                configManager.addDevice(server.arg("ip"), server.arg("brand"));
                server.send(200, "text/html", "<html><body><h1>Device Added! <a href='/'>Back</a></h1></body></html>");
            }
        } else if (server.hasArg("cmd_port")) {
            uint16_t newPort = (uint16_t)server.arg("cmd_port").toInt();
            if (newPort > 1000 && newPort < 65536) {
                configManager.setCommandPort(newPort);
                server.send(200, "text/html",
                    "<html><body><h1>Command Port Updated!</h1>"
                    "<p>New port will be active after device reboot.</p>"
                    "<p><b>Reboot required.</b></p>"
                    "<a href='/'>Back</a></body></html>");
            } else {
                server.send(400, "text/html", "Invalid port. Must be 1001-65535.");
            }
        } else {
            server.send(400, "text/html", "Invalid Data");
        }
    });

    server.on("/clear", HTTP_POST, []() {
        configManager.clearDevices();
        server.send(200, "text/html", "<html><body><h1>Devices Cleared! <a href='/'>Back</a></h1></body></html>");
    });

    server.on("/api/devices", HTTP_GET, [&]() {
        String json = "[";
        std::vector<DeviceConfig> devices = configManager.getDevices();
        for (size_t i = 0; i < devices.size(); i++) {
            if (i > 0) json += ",";
            json += "{\"ip\":\"" + devices[i].ip + "\",\"brand\":\"" + devices[i].brand + "\"}";
        }
        json += "]";
        server.send(200, "application/json", json);
    });

    server.on("/api/config", HTTP_GET, [&]() {
        uint16_t port = configManager.getCommandPort();
        String json = "{\"command_port\":" + String(port) + ",\"command_port_note\":\"Reboot required after change\"}";
        server.send(200, "application/json", json);
    });

    server.on("/api/device", HTTP_GET, [&]() {
        if (server.hasArg("idx")) {
            int idx = server.arg("idx").toInt();
            std::vector<DeviceConfig> devices = configManager.getDevices();
            if (idx >= 0 && idx < (int)devices.size()) {
                String json = "{\"ip\":\"" + devices[idx].ip + "\",\"brand\":\"" + devices[idx].brand + "\"}";
                server.send(200, "application/json", json);
            } else {
                server.send(404, "application/json", "{\"error\":\"Not found\"}");
            }
        } else {
            server.send(400, "application/json", "{\"error\":\"Missing idx param\"}");
        }
    });

    server.on("/api/device", HTTP_DELETE, [&]() {
        if (server.hasArg("idx")) {
            int idx = server.arg("idx").toInt();
            std::vector<DeviceConfig> devices = configManager.getDevices();
            if (idx >= 0 && idx < (int)devices.size()) {
                devices.erase(devices.begin() + idx);
                configManager.saveDevices(devices);
                server.send(200, "application/json", "{\"status\":\"deleted\"}");
            } else {
                server.send(404, "application/json", "{\"error\":\"Not found\"}");
            }
        } else {
            server.send(400, "application/json", "{\"error\":\"Missing idx param\"}");
        }
    });

    server.begin();
    commandServer.begin();
    Serial.print("Web Server on port 80, Command Server on port ");
    Serial.println(cmdPort);
}

void loop() {
    server.handleClient();
    handleWiFiDisconnect();

    // Handle one-shot command server clients (non-blocking)
    if (commandServer.hasClient()) {
        WiFiClient cmdClient = commandServer.available();
        handleCommandClient(cmdClient);
    }

    unsigned long currentMillis = millis();
    if (currentMillis - lastScanTime >= scanInterval) {
        lastScanTime = currentMillis;

        Serial.println("Checking configured devices...");

        std::vector<DeviceConfig> configDevices = configManager.getDevices();
        std::vector<String> currentlyActiveBrands;

        for (const auto& dev : configDevices) {
            if (!NetworkScanner::isValidDevice(Device{dev.ip, dev.brand})) continue;

            IPAddress ip;
            if (ip.fromString(dev.ip)) {
                if (liveness.isAlive(ip)) {
                    lastSeen[dev.brand] = millis();
                    currentlyActiveBrands.push_back(dev.brand);
                }
            }
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

            led.setColor(getColorForBrand(winner));
        }
    }
}