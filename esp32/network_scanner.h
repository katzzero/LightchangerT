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
        // Use lwip to get ARP table entry
        // Note: This is a placeholder - real impl requires esp_netif APIs
        // For now, return empty and rely on static list or other discovery
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