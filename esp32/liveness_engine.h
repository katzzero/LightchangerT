#ifndef LIVENESS_ENGINE_H
#define LIVENESS_ENGINE_H

#include <WiFi.h>
#include <ESPping.h> // Assuming the use of the ESPping library for ICMP
#include "config.h"

class LivenessEngine {
public:
    bool isAlive(IPAddress ip) {
        // Ping the address using ESPping library
        return Ping.ping(ip, 1);
    }
};

#endif