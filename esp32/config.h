#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>
#include <vector>
#include <string>

// Hardware Configuration
const int LED_PIN = 13;
const int NUM_LEDS = 30;
const int BRIGHTNESS = 128;

// Network Configuration
const int SCAN_INTERVAL_MS = 30000;
const int OFFLINE_THRESHOLD = 3;

// MDNS Hostname (used in both STA and AP modes)
const char* MDNS_HOSTNAME = "lightchanger";

// Remote Command Configuration
const int COMMAND_PORT_DEFAULT = 10001;

// Web UI Authentication (stored in NVS under separate keys from WiFi)
const char* NVS_KEY_WEB_USER = "web_user";
const char* NVS_KEY_WEB_PASS = "web_pass";

// Color Mapping (RGB)
struct Color {
    uint8_t r, g, b;
};

const Color COLOR_SONY = {0, 0, 255};
const Color COLOR_MICROSOFT = {0, 255, 0};
const Color COLOR_NINTENDO = {255, 0, 0};
const Color COLOR_STEAM = {0, 191, 255};
const Color COLOR_NVIDIA = {144, 238, 144};
const Color COLOR_DEFAULT = {255, 255, 255};

const int NUM_BRAND_COLORS = 6;
const char* BRAND_NAMES[] = {"sony", "microsoft", "nintendo", "steam", "nvidia", "default"};
const Color BRAND_COLORS[] = {COLOR_SONY, COLOR_MICROSOFT, COLOR_NINTENDO, COLOR_STEAM, COLOR_NVIDIA, COLOR_DEFAULT};

// Steam Detection
const int STEAM_PORT = 27036;
const int STEAM_PORT_2 = 27016;
const int STEAM_PORT_3 = 27017;
const int STEAM_PORT_4 = 27015;
const int STEAM_PORT_5 = 54985;
const int STEAM_TOTAL_PORTS = 5;
const int STEAM_PORTS[] = {STEAM_PORT, STEAM_PORT_2, STEAM_PORT_3, STEAM_PORT_4, STEAM_PORT_5};
const char* STEAM_MDNS_HOSTNAME = "steamdeck.local";
const char* STEAM_MDNS_HOSTNAME_2 = "steam-pc.local";
const char* STEAM_MDNS_HOSTNAME_3 = "steam-deck.local";
const int STEAM_MDNS_TOTAL = 3;
const char* STEAM_MDNS_HOSTNAMES[] = {STEAM_MDNS_HOSTNAME, STEAM_MDNS_HOSTNAME_2, STEAM_MDNS_HOSTNAME_3};
const int STEAM_PROBE_TIMEOUT_MS = 1000;
const int STEAM_RETRY_COUNT = 2;

#endif