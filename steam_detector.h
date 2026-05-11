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
         // Try multiple Steam ports with retries
        for (int attempt = 0; attempt < STEAM_RETRY_COUNT; attempt++) {
             // 1. mDNS discovery
            for (int h = 0; h < STEAM_MDNS_TOTAL; h++) {
                IPAddress dnsIp = MDNS.queryHost(STEAM_MDNS_HOSTNAMES[h], 2000);
                if (dnsIp != IPAddress(0,0,0,0)) {
                    if (probePort(dnsIp)) {
                        return true;
                      }
                   }
               }

             // 2. Port probe on active IPs
            for (const auto& ip : activeIps) {
                if (probePort(ip)) {
                    return true;
                  }
                // Small delay between IPs to avoid overwhelming
                delay(100);
               }
           }
        return false;
      }

private:
    bool probePort(IPAddress ip) {
        WiFiClient client;
         int count = 0;
        while (count < STEAM_TOTAL_PORTS) {
            int port = STEAM_PORTS[count];
            if (client.connect(ip, port)) {
                client.stop();
                return true;
               }
            delay(STEAM_PROBE_TIMEOUT_MS / STEAM_TOTAL_PORTS);
            count++;
           }
        return false;
      }
};

#endif
