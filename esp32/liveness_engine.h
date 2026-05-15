#ifndef LIVENESS_ENGINE_H
#define LIVENESS_ENGINE_H

#include <WiFi.h>
#include <ESPping.h>
#include "config.h"

class LivenessEngine {
public:
    bool isAlive(IPAddress ip) {
        // Ping with 1 attempt and 1 second timeout to minimize blocking
        return Ping.ping(ip, 1, 1000);
    }
};

#endif
