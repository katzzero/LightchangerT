#ifndef NETWORK_SCANNER_H
#define NETWORK_SCANNER_H

#include <Arduino.h>

struct Device {
    String ip;
    String brand;
};

class NetworkScanner {
public:
     // No network scanning - devices are static
     // Devices are provided by ConfigManager via esp32.ino
    static bool isValidDevice(const Device& device) {
        if (device.ip == "" || device.brand == "") return false;
        
         // Basic IP validation
        bool hasDots = false;
        bool hasDigits = false;
        for (char c : device.ip) {
            if (c == '.') hasDots = true;
            if (c >= '0' && c <= '9') hasDigits = true;
          }
        return hasDots && hasDigits;
       }
};

#endif