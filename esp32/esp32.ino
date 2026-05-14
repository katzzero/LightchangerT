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
#include <Preferences.h>

#include "config.h"
#include "led_controller.h"
#include "config_manager.h"
#include "liveness_engine.h"
#include "steam_detector.h"
#include "network_scanner.h"
#include "web_ui.h"
#include "ota_fw_update.h"
#include "basic_auth.h"

LEDController led;
ConfigManager configManager;
LivenessEngine liveness;
SteamDetector steam;

WebServer server(80);
WiFiServer commandServer(COMMAND_PORT_DEFAULT);

std::map<String, unsigned long> lastSeen;
std::map<String, int> missedCycles;

unsigned long lastScanTime = 0;
const unsigned long scanInterval = SCAN_INTERVAL_MS;

bool wifiConnected = false;
bool wifiReconnecting = false;
unsigned long wifiReconnectStart = 0;
const unsigned long WIFI_RECONNECT_INTERVAL = 5000;
const unsigned long WIFI_CONNECT_TIMEOUT = 15000;

// Auth credentials (loaded from NVS or defaults)
String wwwUsername = "";
String wwwPassword = "";
bool authEnabled = false;

Color getColorForBrand(String brand) {
    for (int i = 0; i < NUM_BRAND_COLORS; i++) {
        if (brand.equalsIgnoreCase(String(BRAND_NAMES[i]))) {
            return BRAND_COLORS[i];
        }
    }
    return COLOR_DEFAULT;
}

// ---- Non-blocking WiFi connection attempt ----
void trySTAConnect() {
    String ssid = configManager.getWifiSSID();
    String pass = configManager.getWifiPassword();

    if (ssid.length() == 0) {
        Serial.println("No WiFi SSID configured");
        return;
    }

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid.c_str(), pass.c_str());

    Serial.print("Connecting to WiFi: ");
    Serial.println(ssid);

    wifiConnectStart = millis();
    wifiReconnecting = true;
}

void handleWiFiDisconnect() {
    if (WiFi.status() != WL_CONNECTED) {
        if (!wifiReconnecting) {
            Serial.println("WiFi disconnected. Reconnecting...");
            WiFi.disconnect(false);
            trySTAConnect();
        }
        if (millis() - wifiReconnectStart >= WIFI_CONNECT_TIMEOUT) {
            Serial.println("WiFi reconnect timed out, retrying...");
            wifiReconnectStart = millis();
            WiFi.disconnect(false);
            WiFi.begin(configManager.getWifiSSID().c_str(), configManager.getWifiPassword().c_str());
        }
    } else {
        if (wifiReconnecting) {
            Serial.println("\nWiFi Connected!");
            Serial.print("IP: ");
            Serial.println(WiFi.localIP());
            wifiReconnecting = false;
        }
        wifiConnected = true;
    }
}

// ---- Command processing ----
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

    if (cmd == "HELP") {
        return "Commands: COLOR:<name>, RGB:<r,g,b>, OFF, STATUS?, HELP";
    }

    return "ERR:UNKNOWN";
}

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

// ---- Web server with auth ----
void handleRoot() {
    if (authEnabled && !server.authenticate(wwwUsername.c_str(), wwwPassword.c_str())) {
        return server.requestAuthentication();
    }
    server.send(200, "text/html", INDEX_HTML);
}

void handleSave() {
    if (authEnabled && !server.authenticate(wwwUsername.c_str(), wwwPassword.c_str())) {
        return server.requestAuthentication();
    }

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
}

void handleClear() {
    if (authEnabled && !server.authenticate(wwwUsername.c_str(), wwwPassword.c_str())) {
        return server.requestAuthentication();
    }
    configManager.clearDevices();
    server.send(200, "text/html", "<html><body><h1>Devices Cleared! <a href='/'>Back</a></h1></body></html>");
}

void handleDevices() {
    if (authEnabled && !server.authenticate(wwwUsername.c_str(), wwwPassword.c_str())) {
        return server.requestAuthentication();
    }
    String json = "[";
    std::vector<DeviceConfig> devices = configManager.getDevices();
    for (size_t i = 0; i < devices.size(); i++) {
        if (i > 0) json += ",";
        json += "{\"ip\":\"" + devices[i].ip + "\",\"brand\":\"" + devices[i].brand + "\"}";
    }
    json += "]";
    server.send(200, "application/json", json);
}

void handleConfig() {
    if (authEnabled && !server.authenticate(wwwUsername.c_str(), wwwPassword.c_str())) {
        return server.requestAuthentication();
    }
    uint16_t port = configManager.getCommandPort();
    String json = "{\"command_port\":" + String(port) + ",\"command_port_note\":\"Reboot required after change\"}";
    server.send(200, "application/json", json);
}

void handleDeviceGet() {
    if (authEnabled && !server.authenticate(wwwUsername.c_str(), wwwPassword.c_str())) {
        return server.requestAuthentication();
    }
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
}

void handleDeviceDelete() {
    if (authEnabled && !server.authenticate(wwwUsername.c_str(), wwwPassword.c_str())) {
        return server.requestAuthentication();
    }
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
}

void handleNotFound() {
    server.sendHeader("Location", "http://lightchanger.local", true);
    server.send(302, "text/html", "");
}

// ---- Captive Portal AP mode ----
unsigned long apConnectStart = 0;
const unsigned long AP_CONNECT_TIMEOUT = 15000;

bool shouldStartAPMode() {
    if (!configManager.hasWifiCredentials()) {
        Serial.println("No WiFi credentials stored - starting AP mode");
        return true;
    }
    if (configManager.getFailedAttempts() >= 5) {
        Serial.println("Too many failed connection attempts - starting AP mode");
        return true;
    }
    return false;
}

void startAPMode() {
    WiFi.mode(WIFI_AP);
    WiFi.softAP("Lightchanger-Setup", "lightchanger");

    IPAddress IP = WiFi.softAPIP();
    Serial.print("AP Mode - Connect to: Lightchanger-Setup");
    Serial.print(" AP IP: ");
    Serial.println(IP);

    if (!MDNS.begin("lightchanger")) {
        Serial.println("Error setting up mDNS in AP mode");
    }

    server.on("/", HTTP_GET, []() {
        String ssid = configManager.getWifiSSID();
        String scanInterval = String(configManager.getScanInterval());
        String brightness = String(configManager.getLedBrightness());

        server.send(200, "text/html",
            "<!DOCTYPE html><html><head>"
            "<title>LightchangerT Setup</title>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<style>"
            "body{background:#121212;color:#e0e0e0;font-family:sans-serif;margin:0;padding:20px;}"
            ".card{max-width:500px;margin:40px auto;background:#1e1e1e;padding:30px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.5);}"
            "h1{color:#bb86fc;text-align:center;font-size:24px;}"
            "p.subtitle{text-align:center;color:#888;margin-bottom:25px;}"
            "label{display:block;margin-top:15px;font-weight:bold;color:#bb86fc;font-size:14px;}"
            "input,select{width:100%;padding:12px;margin-top:5px;background:#2d2d2d;border:1px solid #444;color:white;border-radius:6px;box-sizing:border-box;font-size:16px;}"
            "button{width:100%;padding:14px;margin-top:25px;background-color:#bb86fc;color:black;border:none;border-radius:6px;cursor:pointer;font-size:16px;font-weight:bold;}"
            "button:hover{background-color:#9965f4;}"
            ".info{background:#2d2d2d;padding:12px;border-radius:6px;margin-top:15px;font-size:13px;color:#aaa;}"
            "</style></head><body>"
            "<div class='card'>"
            "<h1>&#128161; LightchangerT Setup</h1>"
            "<p class='subtitle'>Connect to your Wi-Fi network</p>"
            "<form method='post' action='/network/save'>"
            "<label>Wi-Fi Network Name (SSID)</label>"
            "<input type='text' name='ssid' value='" + ssid + "' placeholder='Your WiFi SSID' required maxlength='32'>"
            "<label>Password</label>"
            "<input type='password' name='password' placeholder='WiFi password' maxlength='63'>"
            "<div class='info'>"
            "Scan Interval:<br>"
            "<input type='number' name='scan_interval' value='" + scanInterval + "' min='5' max='3600' style='margin-top:5px;'>"
            "</div>"
            "<div class='info'>"
            "LED Brightness (0-255):<br>"
            "<input type='number' name='brightness' value='" + brightness + "' min='0' max='255' style='margin-top:5px;'>"
            "</div>"
            "<button type='submit'>Save & Connect</button>"
            "</form>"
            "<p style='font-size:12px;color:#888;text-align:center;margin-top:20px;'>ESP32 will reboot after saving.</p>"
            "</div></body></html>");
    });

    server.on("/network/save", HTTP_POST, handleNetworkSave);
    server.onNotFound(handleNotFound);
    server.begin();
}

void handleNetworkSave() {
    if (server.hasArg("ssid") && server.arg("ssid").length() > 0) {
        String ssid = server.arg("ssid");
        String password = server.hasArg("password") ? server.arg("password") : "";
        int scanInterval = server.hasArg("scan_interval") ? server.arg("scan_interval").toInt() : 30;
        int brightness = server.hasArg("brightness") ? server.arg("brightness").toInt() : 128;

        configManager.setWifiCredentials(ssid, password);
        configManager.setScanInterval(scanInterval);
        configManager.setLedBrightness(brightness);
        configManager.resetFailedAttempts();

        server.send(200, "text/html",
            "<!DOCTYPE html><html><head><title>Saved</title></head>"
            "<body style='background:#121212;color:#e0e0e0;font-family:sans-serif;text-align:center;padding:40px;'>"
            "<h1 style='color:#bb86fc;'>&#9989; Settings Saved!</h1>"
            "<p>ESP32 will reboot now to connect to:<br><b>" + ssid + "</b></p>"
            "</body></html>");

        delay(1000);
        ESP.restart();
    } else {
        server.send(400, "text/html", "<html><body><h1>SSID is required!</h1><a href='/'>Back</a></body></html>");
    }
}

void setup() {
    Serial.begin(115200);
    led.begin();
    setBkgColor();

    // Load config from NVS
    configManager.begin();

    // Load auth settings
    wwwUsername = configManager.getWifiSSID();
    wwwPassword = configManager.getWifiPassword();
    authEnabled = configManager.getWifiPassword().length() > 0;

    // Load command port from NVS
    uint16_t cmdPort = configManager.getCommandPort();
    commandServer = WiFiServer(cmdPort);

    if (!MDNS.begin("lightchanger-esp32")) {
        Serial.println("Error setting up MDNS responder!");
    }

    // Setup web server routes
    server.on("/", handleRoot);
    server.on("/save", HTTP_POST, handleSave);
    server.on("/clear", HTTP_POST, handleClear);
    server.on("/api/devices", HTTP_GET, handleDevices);
    server.on("/api/config", HTTP_GET, handleConfig);
    server.on("/api/device", HTTP_GET, handleDeviceGet);
    server.on("/api/device", HTTP_DELETE, handleDeviceDelete);
    server.onNotFound(handleNotFound);

    // Check for captive portal mode
    bool apMode = shouldStartAPMode();
    if (apMode) {
        startAPMode();
    } else {
        trySTAConnect();
    }

    server.begin();
    commandServer.begin();

    // Start OTA
    begin_ota();

    Serial.print("Web Server on port 80, Command Server on port ");
    Serial.println(cmdPort);
    if (apMode) Serial.println("Running in AP/Setup mode");
}

void loop() {
    server.handleClient();

    // Handle OTA updates
    handle_ota();

    // Handle WiFi reconnection
    handleWiFiDisconnect();

    // Handle one-shot command server clients (non-blocking)
    if (commandServer.hasClient()) {
        WiFiClient cmdClient = commandServer.available();
        handleCommandClient(cmdClient);
    }

    // Scan loop
    unsigned long currentMillis = millis();
    if (currentMillis - lastScanTime >= scanInterval) {
        lastScanTime = currentMillis;

        if (!wifiConnected) {
            led.setColor(COLOR_DEFAULT);
            return;
        }

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

        // Clean up stale brands
        int offlineThreshold = configManager.getOfflineThreshold();
        for (auto it = lastSeen.begin(); it != lastSeen.end(); ) {
            String brand = it->first;
            bool isActive = false;
            for (const auto& b : currentlyActiveBrands) {
                if (b == brand) { isActive = true; break; }
            }
            if (isActive) {
                missedCycles[brand] = 0;
                ++it;
            } else {
                missedCycles[brand] = missedCycles[brand] + 1;
                if (missedCycles[brand] >= offlineThreshold) {
                    Serial.printf("Removing stale brand '%s' (offline for %d cycles)\n", brand.c_str(), missedCycles[brand]);
                    it = lastSeen.erase(it);
                    missedCycles.erase(brand);
                } else {
                    ++it;
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