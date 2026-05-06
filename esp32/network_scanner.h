#ifndef NETWORK_SCANNER_H
#define NETWORK_SCANNER_H

#include <WiFi.h>
#include <vector>
#include <string>
#include "config.h"

struct Device {
    IPAddress ip;
    String mac;
    String brand;
};

class NetworkScanner {
public:
    std::vector<Device> scan() {
        std::vector<Device> discovered;
        IPAddress localIP = WiFi.localIP();
        
        // Iterate through the subnet (simplification: 1.0.0.1 to 1.0.0.255)
        for (int i = 1; i < 255; i++) {
            IPAddress targetIP = localIP;
            targetIP[3] = i;

            // Attempt to get MAC address using the internal ARP table
            // Note: This depends on the device having been communicated with recently
            String mac = getMacFromIP(targetIP);
            if (mac != "") {
                String brand = identifyBrand(mac);
                if (brand != "") {
                    discovered.push_back({targetIP, mac, brand});
                }
            }
        }
        return discovered;
    }

private:
    String getMacFromIP(IPAddress ip) {
        // Low-level ESP-IDF call to get MAC from ARP table
        uint8_t mac[6];
        if (esp_netif_get_mac_address(ip, mac) == ESP_OK) { // Simplified representative call
            char macStr[18];
            sprintf(macStr, "%02X:%02X:%02X:%02X:%02X:%02X", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
            return String(macStr);
        }
        return "";
    }

    String identifyBrand(String mac) {
        mac.toUpperCase();
        for (const auto& oui : SONY_OUIS) if (mac.startsWith(oui.prefix)) return oui.brand;
        for (const auto& oui : MSFT_OUIS) if (mac.startsWith(oui.prefix)) return oui.brand;
        for (const auto& oui : NINT_OUIS) if (mac.startsWith(oui.prefix)) return oui.brand;
        for (const auto& oui : NVDA_OUIS) if (mac.startsWith(oui.prefix)) return oui.brand;
        return "";
    }
};

#endif