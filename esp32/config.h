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
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";
const int SCAN_INTERVAL_MS = 30000;
const int OFFLINE_THRESHOLD = 3;

// Remote Command Configuration
const int COMMAND_PORT_DEFAULT = 10001;  // TCP port for remote color commands (change requires reboot)

// Color Mapping (RGB)
struct Color {
    uint8_t r, g, b;
};

const Color COLOR_SONY = {0, 0, 255};         // Blue
const Color COLOR_MICROSOFT = {0, 255, 0};    // Green
const Color COLOR_NINTENDO = {255, 0, 0};     // Red
const Color COLOR_STEAM = {0, 191, 255};      // Light Blue
const Color COLOR_NVIDIA = {144, 238, 144};   // Light Green
const Color COLOR_DEFAULT = {255, 255, 255};  // White

// Brand color lookup table for remote commands
const int NUM_BRAND_COLORS = 6;
const char* BRAND_NAMES[] = {"sony", "microsoft", "nintendo", "steam", "nvidia", "default"};
const Color BRAND_COLORS[] = {COLOR_SONY, COLOR_MICROSOFT, COLOR_NINTENDO, COLOR_STEAM, COLOR_NVIDIA, COLOR_DEFAULT};

// MAC OUI Prefixes
struct VendorOUI {
    const char* brand;
    const char* prefix;
};

const std::vector<VendorOUI> SONY_OUIS = {
    {"sony", "00:04:1F"}, {"sony", "00:13:15"}, {"sony", "00:1F:A7"},
    {"sony", "0C:FE:45"}, {"sony", "28:40:DD"}, {"sony", "BC:33:29"}, {"sony", "98:FA:2E"}
};

const std::vector<VendorOUI> MSFT_OUIS = {
    {"microsoft", "00:0D:3A"}, {"microsoft", "00:12:5A"}, {"microsoft", "00:15:5D"},
    {"microsoft", "00:17:FA"}, {"microsoft", "50:1A:C5"}, {"microsoft", "28:18:78"}, {"microsoft", "60:45:BD"}
};

const std::vector<VendorOUI> NINT_OUIS = {
    {"nintendo", "00:09:BF"}, {"nintendo", "00:16:56"}, {"nintendo", "00:1A:E9"},
    {"nintendo", "00:1B:7A"}, {"nintendo", "00:1C:BE"}, {"nintendo", "00:1E:A9"},
    {"nintendo", "00:21:BD"}, {"nintendo", "00:24:F3"}, {"nintendo", "34:AF:2C"},
    {"nintendo", "E8:4E:CE"}, {"nintendo", "CC:FB:65"}, {"nintendo", "58:BD:A3"},
    {"nintendo", "70:48:F7"}, {"nintendo", "70:F0:88"}, {"nintendo", "74:84:69"},
    {"nintendo", "74:F9:CA"}, {"nintendo", "98:B6:E9"}, {"nintendo", "A4:C0:E1"}, {"nintendo", "1C:45:86"}
};

const std::vector<VendorOUI> NVDA_OUIS = {
    {"nvidia", "00:04:4B"}, {"nvidia", "3C:6D:66"}, {"nvidia", "48:B0:2D"},
    {"nvidia", "4C:BB:47"}, {"nvidia", "74:25:54"}, {"nvidia", "AC:3A:E2"}, {"nvidia", "C4:70:BD"}
};

// Steam Detection
const int STEAM_PORT = 27036;
const int STEAM_PORT_2 = 27016;
const int STEAM_PORT_3 = 27017;
const int STEAM_PORT_4 = 27015;
const int STEAM_TOTAL_PORTS = 4;
const int STEAM_PORTS[] = {STEAM_PORT, STEAM_PORT_2, STEAM_PORT_3, STEAM_PORT_4};
const char* STEAM_MDNS_HOSTNAME = "steamdeck.local";
const char* STEAM_MDNS_HOSTNAME_2 = "steam-pc.local";
const char* STEAM_MDNS_HOSTNAME_3 = "steam-deck.local";
const int STEAM_MDNS_TOTAL = 3;
const char* STEAM_MDNS_HOSTNAMES[] = {STEAM_MDNS_HOSTNAME, STEAM_MDNS_HOSTNAME_2, STEAM_MDNS_HOSTNAME_3};
const int STEAM_PROBE_TIMEOUT_MS = 1000;
const int STEAM_RETRY_COUNT = 2;

#endif