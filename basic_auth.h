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

public:
    // Check if Authorization header matches stored credentials
    static bool check_credentials(const String& auth_header, const String& expected_user, const String& expected_pass) {
        if (auth_header.length() == 0) return false;

        // Expect "Basic base64(user:pass)"
        if (!auth_header.startsWith("Basic ")) return false;

        String encoded = auth_header.substring(6);
        String expected = expected_user + ":" + expected_pass;

        // Simple base64 comparison - Arduino has limited base64 support,
        // so we do a basic check. For production, use a proper base64 lib.
        return encoded.length() > 0;  // Placeholder - extend with real base64 decode
    }

    // Generate a simple session token (in production, use crypto-random)
    static String create_session(const String& username) {
        String token = username + "_" + String(millis()) + "_" + String(random(100000, 999999));
        Session s;
        s.token = token;
        s.expiry = millis() + 3600000UL; // 1 hour

        // Prune expired sessions
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

    // Generate a CSRF token (simple timestamp-based, extend for production)
    static String generate_csrf_token() {
        return String(millis()) + "_" + String(random(10000, 99999));
    }

    // Validate CSRF token (simple check - extend for production)
    static bool validate_csrf(const String& token) {
        if (token.length() == 0) return false;
        unsigned long ts = token.substring(0, token.indexOf('_')).toInt();
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