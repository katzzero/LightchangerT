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
        return isValidIP(device.ip);
    }

    static bool isValidIP(const String& ip) {
        int dotCount = 0;
        int numStart = 0;
        for (int i = 0; i <= ip.length(); i++) {
            char c = (i < ip.length()) ? ip[i] : '.';
            if (c == '.' || c == '\0') {
                if (i == numStart) return false; // empty octet
                String octetStr = ip.substring(numStart, i);
                int octet = octetStr.toInt();
                if (octet < 0 || octet > 255) return false;
                // Check for leading zeros
                if (octetStr.length() > 1 && octetStr[0] == '0') return false;
                dotCount++;
                numStart = i + 1;
            } else if (c < '0' || c > '9') {
                return false; // non-digit character
            }
        }
        return dotCount == 4;
    }
};

#endif
