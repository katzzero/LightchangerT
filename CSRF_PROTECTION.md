# LightchangerT CSRF Protection
# ===============================
# This document describes the CSRF protection strategy for both the ESP32
# and Python web configuration interfaces.

## ESP32 Web UI (web_ui.h)

1. **CSRF Token Generation**: Each time the config page (`/`) is loaded,
   a unique CSRF token is generated and embedded as a hidden form field.
   Token = `millis() + "_" + random(10000, 99999)`

2. **Token Validation**: On POST to `/save`, `/clear`, `/api/device`,
   the server validates the token was issued within the last hour.

3. **Same-Origin Enforcement**: The web server only accepts connections
   from the ESP32's own IP (no external proxy by default).

4. **Session Tokens**: After successful auth (if password configured),
   a session cookie is set. Subsequent requests must include the cookie.

## Python Web Config (web_config.py)

1. When authentication (`web_config_password`) is set in `config.json`,
   the server requires Basic Auth on all endpoints.

2. CSRF tokens are generated per-session and embedded in the HTML form.

3. The `/save` POST endpoint validates the token before applying changes.

## Configuration

In `config.json`:
```json
{
  "network": {
    "web_config_enabled": true,
    "web_config_port": 8080,
    "web_config_password": "optional_password_hash"
  }
}
```

## Limitations

- ESP32 has no TLS; all traffic is plaintext (use on trusted networks only)
- Basic Auth credentials are base64, not encrypted (use HTTPS proxy in production)
- CSRF tokens are time-based, not cryptographic (sufficient for local network)