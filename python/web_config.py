import json
import os
import tempfile
import logging
import hashlib
import hmac
import secrets
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"


# ---- CSRF token storage (in-memory, per-process) ----
_csrf_tokens = set()


def generate_csrf_token():
    """Generate a new CSRF token and store it."""
    token = secrets.token_hex(32)
    _csrf_tokens.add(token)
    return token


def validate_csrf(token):
    """Validate a CSRF token and remove it (single-use)."""
    if token in _csrf_tokens:
        _csrf_tokens.discard(token)
        return True
    return False


def _constant_time_compare(a, b):
    """Constant-time string comparison to prevent timing attacks."""
    if isinstance(a, str):
        a = a.encode("utf-8")
    if isinstance(b, str):
        b = b.encode("utf-8")
    return hmac.compare_digest(a, b)


# ---- Salted password hashing (in-memory, no external deps) ----
def _hash_password(password, salt=None):
    """Hash a password with SHA-256 and optional salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${h}"


def _verify_password(password, stored_hash):
    """Verify a password against a stored hash."""
    if not stored_hash or "$" not in stored_hash:
        return False
    salt, _ = stored_hash.split("$", 1)
    return _constant_time_compare(_hash_password(password, salt), stored_hash)


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <title>LightchangerT Config</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { background-color: #121212; color: #e0e0e0; font-family: sans-serif; margin: 0; padding: 20px; }
    h1 { color: #ffffff; text-align: center; }
    .container { max-width: 800px; margin: 0 auto; background: #1e1e1e; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }
    label { display: block; margin-top: 15px; font-weight: bold; color: #bb86fc; }
    input, select { width: 100%; padding: 10px; margin-top: 5px; background: #2d2d2d; border: 1px solid #444; color: white; border-radius: 4px; box-sizing: border-box; }
    textarea { width: 100%; height: 150px; padding: 10px; margin-top: 5px; background: #2d2d2d; border: 1px solid #444; color: white; border-radius: 4px; font-family: monospace; }
    button { width: 100%; padding: 12px; margin-top: 20px; background-color: #bb86fc; color: black; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold; }
    button:hover { background-color: #9965f4; }
    .status { margin-top: 20px; padding: 10px; background: #333; border-radius: 4px; text-align: center; color: #03dac6; }
    .error { color: #cf6679; }
    .info-box { background: #2d2d2d; padding: 12px; border-radius: 6px; margin-top: 15px; font-size: 13px; color: #aaa; }
    .warning { color: #cf6679; font-size: 13px; margin-top: 10px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>LightchangerT Configuration</h1>
    <form method="post" action="/save">
      <input type="hidden" name="csrf_token" value="%(csrf_token)s">

      <label>Network Scan Interval (seconds)</label>
      <input type="number" name="network_scan_interval_seconds" value="%(scan_interval)s" min="1" max="3600">

      <label>Network Detection Mode</label>
      <select name="network_detection_mode">
        <option value="HYBRID" %(mode_hybrid)s>Hybrid</option>
        <option value="STATIC_LIST" %(mode_static)s>Static List Only</option>
        <option value="AUTO" %(mode_auto)s>Auto Discovery</option>
      </select>

      <label>Static Devices (JSON array)</label>
      <textarea name="devices_static_list">%(static_devices)s</textarea>
      <div class="info-box">Format: [{"ip":"...","mac":"...","brand":"..."}, ...]</div>

      <label>Colors (JSON object)</label>
      <textarea name="colors">%(colors)s</textarea>
      <div class="info-box">Format: {"sony":"blue","microsoft":"green",...}</div>

      <label>Hardware Settings (JSON)</label>
      <textarea name="hardware">%(hardware)s</textarea>
      <div class="info-box">Format: {"led_library":"FASTLED","led_pin":13,...}</div>

      <button type="submit">Save Configuration</button>
    </form>
    <div class="status %(status_class)s">%(message)s</div>
  </div>
</body>
</html>"""


class ConfigRequestHandler(BaseHTTPRequestHandler):
    _username = None
    _password_hash = None
    _auth_enabled = False

    @classmethod
    def set_credentials(cls, username, password_hash):
        cls._username = username
        cls._password_hash = password_hash
        cls._auth_enabled = bool(username and password_hash)

    def _check_auth(self):
        """Return True if auth is disabled or credentials match."""
        if not self._auth_enabled:
            return True
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Basic "):
            return False
        import base64
        try:
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        except Exception:
            return False
        parts = decoded.split(":", 1)
        if len(parts) != 2:
            return False
        username, password = parts
        return _constant_time_compare(username, self._username) and _verify_password(password, self._password_hash)

    def _send_auth_challenge(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="LightchangerT Config"')
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<html><body><h1>401 Unauthorized</h1></body></html>")

    def do_GET(self):
        if not self._check_auth():
            return self._send_auth_challenge()

        try:
            cm = _load_config_manager()
            config = cm.get()

            scan_interval = config.get('network', {}).get('scan_interval_seconds', 30)
            mode = config.get('network', {}).get('detection_mode', 'HYBRID')
            static_devices = json.dumps(config.get('devices', {}).get('static_list', []), indent=2)
            colors = json.dumps(config.get('colors', {}), indent=2)
            hardware = json.dumps(config.get('hardware', {}), indent=2)

            csrf_token = generate_csrf_token()

            html = HTML_TEMPLATE % {
                "scan_interval": scan_interval,
                "mode_hybrid": "selected" if mode == "HYBRID" else "",
                "mode_static": "selected" if mode == "STATIC_LIST" else "",
                "mode_auto": "selected" if mode == "AUTO" else "",
                "static_devices": static_devices.replace("<", "&lt;").replace(">", "&gt;"),
                "colors": colors.replace("<", "&lt;").replace(">", "&gt;"),
                "hardware": hardware.replace("<", "&lt;").replace(">", "&gt;"),
                "csrf_token": csrf_token,
                "message": "Current Configuration Loaded",
                "status_class": "",
            }

            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"Error loading config: {e}".encode())

    def do_POST(self):
        if not self._check_auth():
            return self._send_auth_challenge()

        if self.path == "/save":
            self._handle_save()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_save(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 100000:  # 100KB limit
                self.send_error(413, "Payload too large")
                return

            post_data = self.rfile.read(content_length).decode("utf-8")
            params = parse_qs(post_data, keep_blank_values=True)
            params = {k: v[0] if v else "" for k, v in params.items()}

            # Validate CSRF token
            if not validate_csrf(params.get("csrf_token", "")):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Invalid or expired CSRF token")
                return

            cm = _load_config_manager()
            config = cm.get()
            validation_errors = []

            if "network_scan_interval_seconds" in params:
                try:
                    val = int(params["network_scan_interval_seconds"])
                    if 1 <= val <= 3600:
                        if "network" not in config:
                            config["network"] = {}
                        config["network"]["scan_interval_seconds"] = val
                    else:
                        validation_errors.append("Scan interval must be 1-3600")
                except ValueError:
                    validation_errors.append("Invalid scan interval (must be integer)")

            if "network_detection_mode" in params:
                mode = params["network_detection_mode"]
                if mode in ("HYBRID", "STATIC_LIST", "AUTO"):
                    if "network" not in config:
                        config["network"] = {}
                    config["network"]["detection_mode"] = mode
                else:
                    validation_errors.append("Invalid detection mode")

            if "devices_static_list" in params:
                try:
                    devices = json.loads(params["devices_static_list"])
                    if isinstance(devices, list):
                        config["devices"] = config.get("devices", {})
                        config["devices"]["static_list"] = devices
                    else:
                        validation_errors.append("Devices must be a JSON array")
                except json.JSONDecodeError as e:
                    validation_errors.append(f"Invalid JSON in devices: {e}")

            if "colors" in params:
                try:
                    colors = json.loads(params["colors"])
                    if isinstance(colors, dict):
                        config["colors"] = colors
                    else:
                        validation_errors.append("Colors must be a JSON object")
                except json.JSONDecodeError as e:
                    validation_errors.append(f"Invalid JSON in colors: {e}")

            if "hardware" in params:
                try:
                    hardware = json.loads(params["hardware"])
                    if isinstance(hardware, dict):
                        config["hardware"] = hardware
                    else:
                        validation_errors.append("Hardware must be a JSON object")
                except json.JSONDecodeError as e:
                    validation_errors.append(f"Invalid JSON in hardware: {e}")

            if validation_errors:
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                errors_html = "<br>".join(f"&bull; {e}" for e in validation_errors)
                self.wfile.write(f"Validation errors:<br>{errors_html}<br><a href='/'>Back</a>".encode())
                return

            cm.update(config)

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Configuration Saved! <a href='/'>Back</a>")

        except json.JSONDecodeError as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Invalid JSON format: {e}".encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error saving config: {e}".encode())

    def log_message(self, format, *args):
        """Quiet default logging."""
        pass


def _load_config_manager():
    """Load the ConfigManager singleton and return it."""
    from config_manager import get_config_manager
    return get_config_manager()


def run_server(port=80, username=None, password_hash=None):
    """Start the web config server with optional authentication."""
    ConfigRequestHandler.set_credentials(username, password_hash)
    server_address = ("", port)
    httpd = HTTPServer(server_address, ConfigRequestHandler)
    logger.info(f"Web Config Server started on port {port} (auth={'enabled' if ConfigRequestHandler._auth_enabled else 'disabled'})")
    httpd.serve_forever()