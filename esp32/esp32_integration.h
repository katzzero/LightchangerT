// OTA + Auth integrated update for esp32.ino
// Add these includes and modifications to existing esp32.ino

// --- Add to includes section ---
#include "ota_fw_update.h"
#include "basic_auth.h"

// --- Add to global variables ---
const char* www_username = "";  // Set from NVS or config
const char* www_password = "";

// --- Replace setup() WiFi section with non-blocking version ---
void setup() {
    Serial.begin(115200);
    led.begin();

    // Load config first
    configManager.begin();

    // Load credentials from NVS
    www_username = configManager.getWifiSSID().c_str();
    www_password = configManager.getWifiPassword().c_str();

    uint16_t cmdPort = configManager.getCommandPort();
    commandServer = WiFiServer(cmdPort);

    // Try STA connection
    WiFi.mode(WIFI_STA);
    WiFi.begin(configManager.getWifiSSID().c_str(), configManager.getWifiPassword().c_str());

    Serial.print("Connecting to WiFi");
    wifiConnectStart = millis();

    while (millis() - wifiConnectStart < WIFI_CONNECT_TIMEOUT) {
        if (WiFi.status() == WL_CONNECTED) {
            Serial.println("\nWiFi Connected!");
            Serial.print("IP: ");
            Serial.println(WiFi.localIP());
            wifiConnected = true;
            break;
        }
        Serial.print(".");
        delay(500);
    }

    if (!wifiConnected) {
        Serial.println("\nWiFi connection timed out");
        configManager.incrementFailedAttempts();
        if (configManager.getFailedAttempts() >= MAX_FAILED_ATTEMPTS) {
            Serial.println("Too many failures - starting AP mode");
            startAPMode();
        }
    }

    lastScanTime = millis();

    // Start Web Server with authentication
    server.on("/", HTTP_GET, handleRoot);
    server.on("/save", HTTP_POST, handleSave);
    server.on("/clear", HTTP_POST, handleClear);
    server.on("/api/devices", HTTP_GET, handleDevices);
    server.on("/api/config", HTTP_GET, handleConfig);
    server.on("/api/device", HTTP_GET, handleDeviceGet);
    server.on("/api/device", HTTP_DELETE, handleDeviceDelete);
    server.onNotFound(handleNotFound);

    server.begin();
    commandServer.begin();

    // Start OTA
    begin_ota();

    Serial.print("Web Server on port 80, Command Server on port ");
    Serial.println(cmdPort);
}

// --- Add to loop() right after server.handleClient() ---
void loop() {
    server.handleClient();
    handleWiFiDisconnect();

    // Handle one-shot command server clients (non-blocking)
    if (commandServer.hasClient()) {
        WiFiClient cmdClient = commandServer.available();
        handleCommandClient(cmdClient);
    }

    // Handle OTA updates
    handle_ota();

    // Rest of scan logic...
    unsigned long currentMillis = millis();
    if (currentMillis - lastScanTime >= scanInterval) {
        lastScanTime = currentMillis;
        // ... existing scan logic
    }
}

// --- Protected endpoint handlers ---
void handleRoot() {
    if (!check_auth(server)) {
        server.requestAuthentication();
        return;
    }
    server.send(200, "text/html", INDEX_HTML);
}

void handleSave() {
    if (!check_auth(server)) {
        server.requestAuthentication();
        return;
    }
    // ... existing save logic
}

void handleDevices() {
    if (!check_auth(server)) {
        server.requestAuthentication();
        return;
    }
    // ... existing devices logic
}

bool check_auth(WebServer& srv) {
    if (strlen(www_password) == 0) return true;  // No password set = open access
    return srv.authenticate(www_username, www_password);
}