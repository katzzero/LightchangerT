#ifndef CONFIG_MANAGER_H
#define CONFIG_MANAGER_H

#include <Preferences.h>
#include <IPAddress.h>

struct DeviceConfig {
    String ip;
    String brand;
};

class ConfigManager {
private:
    Preferences prefs;
    const char* NVS_NAMESPACE = "lightchanger";

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
};

#endif