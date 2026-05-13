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
    const uint16_t CMD_PORT_DEFAULT = COMMAND_PORT_DEFAULT;

public:
    void begin() {
        prefs.begin(NVS_NAMESPACE, false);
    }

    void addDevice(String ip, String brand) {
        // Format: ip|brand;
        String current = prefs.getString("devices", "");
        current += ip + "|" + brand + ";";
        prefs.putString("devices", current);
    }

    std::vector<DeviceConfig> getDevices() {
        std::vector<DeviceConfig> deviceList;
        String data = prefs.getString("devices", "");
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
        prefs.remove("devices");
    }

    void saveDevices(std::vector<DeviceConfig> devices) {
        String result = "";
        for (int i = 0; i < (int)devices.size(); i++) {
            if (i > 0) result += ";";
            result += devices[i].ip + "|" + devices[i].brand;
        }
        prefs.putString("devices", result);
    }

    uint16_t getCommandPort() {
        return prefs.getShort("cmd_port", CMD_PORT_DEFAULT);
    }

    void setCommandPort(uint16_t port) {
        if (port > 1000 && port < 65536) {
            prefs.putShort("cmd_port", port);
        }
    }
};

#endif