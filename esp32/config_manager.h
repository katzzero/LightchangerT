#ifndef CONFIG_MANAGER_H
#define CONFIG_MANAGER_H

#include <Preferences.h>
#include <IPAddress.h>
#include <vector>
#include "config.h"

struct DeviceConfig {
    String ip;
    String brand;
};

class ConfigManager {
private:
    Preferences prefs;
    const char* NVS_NAMESPACE = "lightchanger";

    static const char* KEY_SSID;
    static const char* KEY_PASSWORD;
    static const char* KEY_SCAN_INTERVAL;
    static const char* KEY_BRIGHTNESS;
    static const char* KEY_FAILED_ATTEMPTS;
    static const char* KEY_DEVICES;
    static const char* KEY_CMD_PORT;
    static const char* KEY_OFFLINE_THRESHOLD;

public:
    void begin() {
        prefs.begin(NVS_NAMESPACE, false);
    }

    // ---- Web UI Authentication (stored separately from WiFi credentials) ----

    void setWebCredentials(String username, String password) {
        if (username.length() > 0) {
            prefs.putString(NVS_KEY_WEB_USER, username);
            prefs.putString(NVS_KEY_WEB_PASS, password);
        } else {
            prefs.remove(NVS_KEY_WEB_USER);
            prefs.remove(NVS_KEY_WEB_PASS);
        }
    }

    String getWebUsername() {
        return prefs.getString(NVS_KEY_WEB_USER, "");
    }

    String getWebPassword() {
        return prefs.getString(NVS_KEY_WEB_PASS, "");
    }

    bool hasWebCredentials() {
        return prefs.getString(NVS_KEY_WEB_USER, "").length() > 0;
    }

    // ---- Device Management ----

    void addDevice(String ip, String brand) {
        String current = prefs.getString(KEY_DEVICES, "");
        current += ip + "|" + brand + ";";
        prefs.putString(KEY_DEVICES, current);
    }

    std::vector<DeviceConfig> getDevices() {
        std::vector<DeviceConfig> deviceList;
        String data = prefs.getString(KEY_DEVICES, "");
        if (data.length() == 0) return deviceList;

        int start = 0;
        int end = data.indexOf(';');
        while (end != -1) {
            String item = data.substring(start, end);
            int sep = item.indexOf('|');
            if (sep != -1) {
                DeviceConfig dev;
                dev.ip = item.substring(0, sep);
                dev.brand = item.substring(sep + 1);
                deviceList.push_back(dev);
            }
            start = end + 1;
            end = data.indexOf(';', start);
        }
        return deviceList;
    }

    void clearDevices() {
        prefs.remove(KEY_DEVICES);
    }

    void saveDevices(std::vector<DeviceConfig> devices) {
        String result = "";
        for (int i = 0; i < (int)devices.size(); i++) {
            if (i > 0) result += ";";
            result += devices[i].ip + "|" + devices[i].brand;
        }
        prefs.putString(KEY_DEVICES, result);
    }

    // ---- Command Port ----

    uint16_t getCommandPort() {
        return prefs.getUShort(KEY_CMD_PORT, COMMAND_PORT_DEFAULT);
    }

    void setCommandPort(uint16_t port) {
        if (port > 1000 && port < 65536) {
            prefs.putUShort(KEY_CMD_PORT, port);
        }
    }

    // ---- WiFi Credentials ----

    void setWifiCredentials(String ssid, String password) {
        prefs.putString(KEY_SSID, ssid);
        prefs.putString(KEY_PASSWORD, password);
    }

    String getWifiSSID() {
        return prefs.getString(KEY_SSID, "");
    }

    String getWifiPassword() {
        return prefs.getString(KEY_PASSWORD, "");
    }

    bool hasWifiCredentials() {
        return prefs.getString(KEY_SSID, "").length() > 0;
    }

    void clearWifiCredentials() {
        prefs.remove(KEY_SSID);
        prefs.remove(KEY_PASSWORD);
    }

    // ---- Scan Interval ----

    void setScanInterval(int seconds) {
        if (seconds >= 5 && seconds <= 3600) {
            prefs.putInt(KEY_SCAN_INTERVAL, seconds);
        }
    }

    int getScanInterval() {
        return prefs.getInt(KEY_SCAN_INTERVAL, SCAN_INTERVAL_MS / 1000);
    }

    // ---- LED Brightness ----

    void setLedBrightness(int brightness) {
        if (brightness >= 0 && brightness <= 255) {
            prefs.putUChar(KEY_BRIGHTNESS, (uint8_t)brightness);
        }
    }

    int getLedBrightness() {
        return prefs.getUChar(KEY_BRIGHTNESS, BRIGHTNESS);
    }

    // ---- Failed Connection Attempts (for captive portal fallback) ----

    void incrementFailedAttempts() {
        int current = getFailedAttempts();
        prefs.putInt(KEY_FAILED_ATTEMPTS, current + 1);
    }

    void resetFailedAttempts() {
        prefs.putInt(KEY_FAILED_ATTEMPTS, 0);
    }

    int getFailedAttempts() {
        return prefs.getInt(KEY_FAILED_ATTEMPTS, 0);
    }

    // ---- Offline Threshold ----

    void setOfflineThreshold(int cycles) {
        if (cycles >= 1 && cycles <= 100) {
            prefs.putInt(KEY_OFFLINE_THRESHOLD, cycles);
        }
    }

    int getOfflineThreshold() {
        return prefs.getInt(KEY_OFFLINE_THRESHOLD, OFFLINE_THRESHOLD);
    }
};

// Define static key constants
const char* ConfigManager::KEY_SSID = "wifi_ssid";
const char* ConfigManager::KEY_PASSWORD = "wifi_pass";
const char* ConfigManager::KEY_SCAN_INTERVAL = "scan_interval";
const char* ConfigManager::KEY_BRIGHTNESS = "led_brightness";
const char* ConfigManager::KEY_FAILED_ATTEMPTS = "fail_count";
const char* ConfigManager::KEY_DEVICES = "devices";
const char* ConfigManager::KEY_CMD_PORT = "cmd_port";
const char* ConfigManager::KEY_OFFLINE_THRESHOLD = "offline_thr";

#endif