#include <Arduino.h>
#include <map>
#include <WiFi.h>
#include <WebServer.h>
#include <FastLED.h>
#include <ESPping.h>
#include <ESPmDNS.h>

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

std::map<String, unsigned long> lastSeen;

unsigned long lastScanTime = 0;
const unsigned long scanInterval = SCAN_INTERVAL_MS;

bool wifiConnected = false;

bool wifiReconnecting = false;
unsigned long wifiReconnectStart = 0;
const unsigned long WIFI_RECONNECT_INTERVAL = 5000;

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

Color getColorForBrand(String brand) {
    static std::map<String, Color> brandColors = {
         {"sony", COLOR_SONY},
         {"microsoft", COLOR_MICROSOFT},
         {"nintendo", COLOR_NINTENDO},
         {"steam", COLOR_STEAM},
         {"nvidia", COLOR_NVIDIA}
     };

    auto it = brandColors.find(brand);
    if (it != brandColors.end()) return it->second;
    return COLOR_DEFAULT;
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

    if (!MDNS.begin("lightchanger-esp32")) {
        Serial.println("Error setting up MDNS responder!");
      }
    
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
                 if (editIdx < devices.size()) {
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
           for (int i = 0; i < devices.size(); i++) {
               if (i > 0) json += ",";
               json += "{\"ip\":\"" + devices[i].ip + "\",\"brand\":\"" + devices[i].brand + "\"}";
                  }
           json += "]";
           server.send(200, "application/json", json);
            });
    server.on("/api/device", HTTP_GET, [&]() {
          if (server.hasArg("idx")) {
              int idx = server.arg("idx").toInt();
              std::vector<DeviceConfig> devices = configManager.getDevices();
              if (idx >= 0 && idx < devices.size()) {
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
              if (idx >= 0 && idx < devices.size()) {
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
    Serial.println("Web Server started on port 80");
   }

void loop() {
    server.handleClient();
    handleWiFiDisconnect();

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
                     Serial.print("Device Online: ");
                     Serial.println(dev.ip);
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
