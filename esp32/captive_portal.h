#ifndef CAPTIVE_PORTAL_H
#define CAPTIVE_PORTAL_H

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include "config.h"
#include "config_manager.h"

// Maximum consecutive connection failures before triggering AP mode
const int MAX_FAILED_ATTEMPTS = 5;

// AP credentials shown to user for initial setup
const char* AP_SSID = "Lightchanger-Setup";
const char* AP_PASSWORD = "lightchanger";

extern ConfigManager configManager;
extern WebServer server;

// Non-blocking delay tracking for WiFi connection attempts
unsigned long wifiConnectStart = 0;
const unsigned long WIFI_CONNECT_TIMEOUT = 15000;  // 15 seconds per attempt

// Forward declarations
void handleNetworkSave();
void handleNotFound();

// Check if we should start in AP mode based on stored config and failure count
bool shouldStartAPMode() {
    if (!configManager.hasWifiCredentials()) {
        Serial.println("No WiFi credentials stored - starting AP mode");
        return true;
    }

    if (configManager.getFailedAttempts() >= MAX_FAILED_ATTEMPTS) {
        Serial.println("Too many failed connection attempts - starting AP mode");
        return true;
    }

    return false;
}

// Start Access Point mode for captive portal
void startAPMode() {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASSWORD);

    IPAddress IP = WiFi.softAPIP();
    Serial.print("AP Mode - Connect to: ");
    Serial.println(AP_SSID);
    Serial.print("AP IP: ");
    Serial.println(IP);

    // Start DNS to redirect all requests to the ESP32
    if (!MDNS.begin("lightchanger")) {
        Serial.println("Error setting up mDNS in AP mode");
    }

    // Define web server routes for the setup page
    server.on("/", HTTP_GET, []() {
        String ssid = configManager.getWifiSSID();
        String scanInterval = String(configManager.getScanInterval());
        String brightness = String(configManager.getLedBrightness());

        server.send(200, "text/html",
            "<!DOCTYPE html>"
            "<html><head>"
            "<title>LightchangerT Setup</title>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<style>"
            "body { background: #121212; color: #e0e0e0; font-family: sans-serif; margin: 0; padding: 20px; }"
            ".card { max-width: 500px; margin: 40px auto; background: #1e1e1e; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }"
            "h1 { color: #bb86fc; text-align: center; font-size: 24px; }"
            "p.subtitle { text-align: center; color: #888; margin-bottom: 25px; }"
            "label { display: block; margin-top: 15px; font-weight: bold; color: #bb86fc; font-size: 14px; }"
            "input, select { width: 100%; padding: 12px; margin-top: 5px; background: #2d2d2d; border: 1px solid #444; color: white; border-radius: 6px; box-sizing: border-box; font-size: 16px; }"
            "button { width: 100%; padding: 14px; margin-top: 25px; background-color: #bb86fc; color: black; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; }"
            "button:hover { background-color: #9965f4; }"
            ".note { font-size: 12px; color: #888; margin-top: 5px; }"
            ".info { background: #2d2d2d; padding: 12px; border-radius: 6px; margin-top: 15px; font-size: 13px; color: #aaa; }"
            "</style>"
            "</head><body>"
            "<div class='card'>"
            "<h1>&#128161; LightchangerT Setup</h1>"
            "<p class='subtitle'>Connect to your Wi-Fi network</p>"
            "<form method='post' action='/network/save'>"
            "<label>Wi-Fi Network Name (SSID)</label>"
            "<input type='text' name='ssid' value='" + ssid + "' placeholder='Your WiFi SSID' required maxlength='32'>"
            "<label>Password</label>"
            "<input type='password' name='password' placeholder='WiFi password' maxlength='63'>"
            "<div class='info'>"
            "&#8635; Scan Interval (seconds):<br>"
            "<input type='number' name='scan_interval' value='" + scanInterval + "' min='5' max='3600' style='margin-top:5px;'>"
            "</div>"
            "<div class='info'>"
            "&#128161; LED Brightness (0-255):<br>"
            "<input type='number' name='brightness' value='" + brightness + "' min='0' max='255' style='margin-top:5px;'>"
            "</div>"
            "<button type='submit'>Save & Connect</button>"
            "</form>"
            "<p class='note' style='text-align:center; margin-top:20px;'>&#9888; ESP32 will reboot after saving to apply settings.</p>"
            "</div>"
            "</body></html>");
    });

    server.on("/network/save", HTTP_POST, handleNetworkSave);
    server.onNotFound(handleNotFound);
    server.begin();
}

// Redirect all HTTP requests to the captive portal
void handleNotFound() {
    server.sendHeader("Location", "http://lightchanger.local", true);
    server.send(302, "text/html", "");
}

// Save network credentials, scan interval, brightness and restart
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
            "<!DOCTYPE html>"
            "<html><head><title>Saved</title></head>"
            "<body style='background:#121212; color:#e0e0e0; font-family:sans-serif; text-align:center; padding:40px;'>"
            "<h1 style='color:#bb86fc;'>&#9989; Settings Saved!</h1>"
            "<p>ESP32 will reboot now to connect to:<br>"
            "<b>" + ssid + "</b></p>"
            "<p style='color:#888; margin-top:20px;'>If it doesn't reconnect, try reconnecting to the 'Lightchanger-Setup' AP.</p>"
            "</body></html>");

        delay(1000);
        ESP.restart();
    } else {
        server.send(400, "text/html", "<html><body><h1>SSID is required!</h1><a href='/'>Back</a></body></html>");
    }
}

// Attempt STA connection with timeout, returns true on success
bool trySTAConnect(ConfigManager& cfg) {
    String ssid = cfg.getWifiSSID();
    String pass = cfg.getWifiPassword();

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid.c_str(), pass.c_str());

    Serial.print("Connecting to WiFi: ");
    Serial.println(ssid);

    wifiConnectStart = millis();

    while (millis() - wifiConnectStart < WIFI_CONNECT_TIMEOUT) {
        if (WiFi.status() == WL_CONNECTED) {
            Serial.println("\nWiFi Connected!");
            Serial.print("IP: ");
            Serial.println(WiFi.localIP());
            return true;
        }
        delay(200);
        Serial.print(".");
    }

    Serial.println("\nWiFi connection timed out");
    return false;
}

#endif