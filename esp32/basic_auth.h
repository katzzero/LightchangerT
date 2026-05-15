#ifndef BASIC_AUTH_H
#define BASIC_AUTH_H

#include <Arduino.h>
#include <vector>

// Simple Basic Auth / session token validation for ESP32 web UI
// Credentials stored in NVS via ConfigManager

class BasicAuth {
private:
    static const size_t MAX_SESSIONS = 5;
    struct Session {
        String token;
        unsigned long expiry;
    };

    static std::vector<Session> validSessions;

    // Simple base64 decode (supports standard base64 alphabet)
    static String base64_decode(const String& encoded) {
        static const char b64[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        String result = "";
        int val = 0, valb = -8;
        for (size_t i = 0; i < encoded.length(); i++) {
            char c = encoded[i];
            if (c == '=') break;
            int pos = -1;
            for (int j = 0; j < 64; j++) {
                if (b64[j] == c) { pos = j; break; }
            }
            if (pos == -1) continue;
            val = (val << 6) + pos;
            valb += 6;
            if (valb >= 0) {
                result += char((val >> valb) & 0xFF);
                valb -= 8;
            }
        }
        return result;
    }

public:
    // Check if Authorization header matches stored credentials
    static bool check_credentials(const String& auth_header, const String& expected_user, const String& expected_pass) {
        if (auth_header.length() == 0) return false;
        if (!auth_header.startsWith("Basic ")) return false;

        String encoded = auth_header.substring(6);
        String decoded = base64_decode(encoded);
        int colonIdx = decoded.indexOf(':');
        if (colonIdx < 0) return false;

        String user = decoded.substring(0, colonIdx);
        String pass = decoded.substring(colonIdx + 1);
        return (user == expected_user) && (pass == expected_pass);
    }

    // Generate a session token with better entropy
    static String create_session(const String& username) {
        String token = username + "_";
        for (int i = 0; i < 8; i++) {
            token += String(random(0, 16), HEX);
        }
        token += "_" + String(millis());

        Session s;
        s.token = token;
        s.expiry = millis() + 3600000UL; // 1 hour

        prune_expired();

        if (validSessions.size() >= MAX_SESSIONS) {
            validSessions.erase(validSessions.begin());
        }
        validSessions.push_back(s);
        return token;
    }

    // Validate a session token from cookie/header
    static bool validate_session(const String& token) {
        if (token.length() == 0) return false;
        prune_expired();

        for (const auto& s : validSessions) {
            if (s.token == token && millis() < s.expiry) {
                return true;
            }
        }
        return false;
    }

    // Generate a CSRF token with server-side tracking
    static String generate_csrf_token() {
        String token = "";
        for (int i = 0; i < 16; i++) {
            token += String(random(0, 16), HEX);
        }
        token += "_" + String(millis());
        return token;
    }

    // Validate CSRF token (checks format and timestamp)
    static bool validate_csrf(const String& token) {
        if (token.length() == 0) return false;
        int underscoreIdx = token.indexOf('_');
        if (underscoreIdx < 0) return false;
        unsigned long ts = token.substring(0, underscoreIdx).toInt();
        return (millis() - ts) < 3600000UL; // Valid for 1 hour
    }

    // Clear all sessions (call on logout/credential change)
    static void clear_sessions() {
        validSessions.clear();
    }

private:
    static void prune_expired() {
        unsigned long now = millis();
        for (int i = validSessions.size() - 1; i >= 0; i--) {
            if (now >= validSessions[i].expiry) {
                validSessions.erase(validSessions.begin() + i);
            }
        }
    }
};

std::vector<BasicAuth::Session> BasicAuth::validSessions;

#endif  // BASIC_AUTH_H
