#ifndef LIVENESS_ENGINE_H
#define LIVENESS_ENGINE_H

#include <WiFi.h>
#include <ESPping.h> // Assuming the use of the ESPping library for ICMP
#include "config.h"

class LivenessEngine {
public:
    bool isAlive(IPAddress ip) {
        // Ping the address. 
        // ESPping::ping returns true if the host is reachable.
        if (ESPping::ping(ip, 1)) {
            return true;
        }
        return false;
    }
};

#endif