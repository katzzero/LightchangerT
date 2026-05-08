#ifndef STEAM_DETECTOR_H
#define STEAM_DETECTOR_H

#include <WiFi.h>
#include <ESPmDNS.h>
#include <WiFiClient.h>
#include "config.h"

class SteamDetector {
public:
    bool detect(const std::vector<IPAddress>& activeIps) {
        // 1. Attempt mDNS discovery for the hostname
        if (std::string(STEAM_MDNS_HOSTNAME) != "") {
            IPAddress dnsIp = MDNS.queryHost(STEAM_MDNS_HOSTNAME, 2000);
            if (dnsIp != IPAddress(0,0,0,0)) {
                if (probePort(dnsIp)) return true;
            }
        }

        // 2. Port probe check on local network active IPs
        for (const auto& ip : activeIps) {
            if (probePort(ip)) return true;
        }
        return false;
    }

private:
    bool probePort(IPAddress ip) {
        WiFiClient client;
        if (client.connect(ip, STEAM_PORT)) {
            client.stop();
            return true;
        }
        return false;
    }
};

#endif