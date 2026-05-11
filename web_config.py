import json
import os
import logging
import tempfile
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"

HTML_TEMPLATE = """
<!DOCTYPE html>
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
  </style>
</head>
<body>
  <div class="container">
    <h1>LightchangerT Configuration</h1>
    <form method="post" action="/save">
      <label>Network Scan Interval (seconds)</label>
      <input type="number" name="network_scan_interval_seconds" value="%(scan_interval)s">

      <label>Network Detection Mode</label>
      <select name="network_detection_mode">
        <option value="HYBRID" %(mode_hybrid)s>Hybrid</option>
        <option value="STATIC_LIST" %(mode_static)s>Static List Only</option>
        <option value="AUTO" %(mode_auto)s>Auto Discovery</option>
      </select>

      <label>Static Devices (JSON)</label>
      <textarea name="devices_static_list">%(static_devices)s</textarea>
      <small style="color: #888;">Format: [ { "ip": "...", "mac": "...", "brand": "..." }, ... ]</small>

      <label>Colors (JSON)</label>
      <textarea name="colors">%(colors)s</textarea>

      <label>Hardware Settings (JSON)</label>
      <textarea name="hardware">%(hardware)s</textarea>

      <button type="submit">Save Configuration</button>
    </form>
    <div class="status">%(message)s</div>
  </div>
</body>
</html>
"""

class ConfigRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            
            # Format data for template
            scan_interval = config.get('network', {}).get('scan_interval_seconds', 30)
            mode = config.get('network', {}).get('detection_mode', 'HYBRID')
            static_devices = json.dumps(config.get('devices', {}).get('static_list', []), indent=2)
            colors = json.dumps(config.get('colors', {}), indent=2)
            hardware = json.dumps(config.get('hardware', {}), indent=2)
            
            html = HTML_TEMPLATE % {
                "scan_interval": scan_interval,
                "mode_hybrid": "selected" if mode == "HYBRID" else "",
                "mode_static": "selected" if mode == "STATIC_LIST" else "",
                "mode_auto": "selected" if mode == "AUTO" else "",
                "static_devices": static_devices.replace("<", "&lt;").replace(">", "&gt;"),
                "colors": colors.replace("<", "&lt;").replace(">", "&gt;"),
                "hardware": hardware.replace("<", "&lt;").replace(">", "&gt;"),
                "message": "Current Configuration Loaded"
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error loading config: {e}".encode())

    def do_POST(self):
        if self.path == '/save':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')

            try:
                # Parse form data properly using urllib.parse
                params = parse_qs(post_data, keep_blank_values=True)
                # parse_qs returns lists, get first value
                params = {k: v[0] if v else '' for k, v in params.items()}

                with open(CONFIG_FILE, 'r+') as f:
                    config = json.load(f)

                 # Update config with validation
                if 'network_scan_interval_seconds' in params:
                    try:
                        val = int(params['network_scan_interval_seconds'])
                        if 1 <= val <= 3600:
                            config['network']['scan_interval_seconds'] = val
                    except ValueError:
                        raise ValueError("Invalid scan interval")

                if 'network_detection_mode' in params:
                    mode = params['network_detection_mode']
                    if mode in ('HYBRID', 'STATIC_LIST', 'AUTO'):
                        config['network']['detection_mode'] = mode

                if 'devices_static_list' in params:
                    config['devices']['static_list'] = json.loads(params['devices_static_list'])

                if 'colors' in params:
                    config['colors'] = json.loads(params['colors'])

                if 'hardware' in params:
                    config['hardware'] = json.loads(params['hardware'])

                 # Atomic write: write to temp file then rename
                dir_name = os.path.dirname(CONFIG_FILE) or '.'
                fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
                try:
                    with os.fdopen(fd, 'w') as f:
                        json.dump(config, f, indent=2)
                    os.replace(tmp_path, CONFIG_FILE)
                except Exception:
                    os.unlink(tmp_path)
                    raise

                self.send_response(200)
                self.send_header('Content-type', 'text/html')
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

def run_server(port=80):
    server_address = ('', port)
    httpd = HTTPServer(server_address, ConfigRequestHandler)
    logger.info(f"Web Config Server started on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()