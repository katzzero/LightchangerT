#ifndef STEAM_DETECTOR_H
#define STEAM_DETECTOR_H

#include <WiFi.h>
#include <ESPmDNS.h>
#include <WiFiClient.h>
#include <vector>
#include "config.h"

class SteamDetector {
public:
    bool detect(const std::vector<IPAddress>& activeIps) {
        for (int attempt = 0; attempt < STEAM_RETRY_COUNT; attempt++) {
            for (int h = 0; h < STEAM_MDNS_TOTAL; h++) {
                IPAddress dnsIp = MDNS.queryHost(STEAM_MDNS_HOSTNAMES[h], 2000);
                if (dnsIp != IPAddress(0, 0, 0, 0)) {
                    if (probePort(dnsIp)) {
                        return true;
                    }
                }
            }

            for (const auto& ip : activeIps) {
                if (probePort(ip)) {
                    return true;
                }
                delay(10);
            }
        }
        return false;
    }

private:
    bool probePort(IPAddress ip) {
        for (int count = 0; count < STEAM_TOTAL_PORTS; count++) {
            WiFiClient client;
            int port = STEAM_PORTS[count];
            if (client.connect(ip, port)) {
                client.stop();
                return true;
            }
            delay(STEAM_PROBE_TIMEOUT_MS / STEAM_TOTAL_PORTS);
        }
        return false;
    }
};

#endif