import socket
import json
import logging

logger = logging.getLogger(__name__)


class Esp32CommandClient:
    """TCP client for sending color commands to an ESP32 remote device.

    Protocol (text-based, one-shot TCP):
        COLOR:<name>\\n  - Set color by name (e.g., COLOR:blue)
        RGB:<r>,<g>,<b>\\n  - Set color by RGB values
        OFF\\n            - Turn off LED
        STATUS?\\n        - Query current status

    Responses:
        OK                - Command executed
        ERR:UNKNOWN       - Unknown command
        ERR:INVALID_RGB   - Malformed RGB values
        STATUS:<state>    - Status response
    """

    def __init__(self, host, port=10001, timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, command):
        """Send a raw command string and return the response."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout)
                s.connect((self.host, self.port))
                s.sendall((command.strip() + "\n").encode())
                response = s.recv(1024).decode().strip()
                logger.debug(f"ESP32 command '{command.strip()}' -> {response}")
                return response
        except socket.timeout:
            logger.error(f"ESP32 command timeout: {self.host}:{self.port}")
            return "ERR:TIMEOUT"
        except ConnectionRefusedError:
            logger.error(f"ESP32 connection refused at {self.host}:{self.port}")
            return "ERR:CONNECTION_REFUSED"
        except OSError as e:
            logger.error(f"ESP32 connection error: {e}")
            return f"ERR:{e}"

    def set_color(self, color_name):
        """Set LED color by name (e.g., 'blue', 'red', 'steam')."""
        return self.send(f"COLOR:{color_name}")

    def set_rgb(self, r, g, b):
        """Set LED color by RGB values (0-255 each)."""
        return self.send(f"RGB:{int(r)},{int(g)},{int(b)}")

    def off(self):
        """Turn off the LED."""
        return self.send("OFF")

    def status(self):
        """Query current LED status."""
        return self.send("STATUS?")


def get_esp32_client(config):
    """Factory function that returns an Esp32CommandClient from config,
    or None if remote ESP32 control is not configured."""
    esp32_cfg = config.get('esp32_command', {})
    if esp32_cfg.get('enabled', False):
        host = esp32_cfg.get('host', '192.168.1.50')
        port = esp32_cfg.get('port', 10001)
        return Esp32CommandClient(host, port)
    return None