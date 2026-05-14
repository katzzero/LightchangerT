"""
LightchangerT - ESP32 Remote TCP Client
Sends color commands to a remote ESP32 over TCP.

Usage:
    client = ESP32Client(host="192.168.1.50", port=10001)
    client.send_command("COLOR:blue")
    client.send_command("RGB:255,0,0")
    client.send_command("OFF")
    status = client.get_status()
    client.close()

Protocol (text-based, one-shot TCP, newline-delimited):
    Commands:  COLOR:<name>, RGB:<r>,<g>,<b>, OFF, STATUS?
    Responses: OK, ERR:<reason>, STATUS:<state>
"""

import socket
import logging
from typing import Optional, Tuple, Dict

from led_controller import _to_rgb

logger = logging.getLogger(__name__)

DEFAULT_PORT = 10001
DEFAULT_TIMEOUT = 5  # seconds


class ESP32Client:
    """TCP client for sending color commands to a remote ESP32."""

    def __init__(self, host: str, port: int = DEFAULT_PORT, timeout: int = DEFAULT_TIMEOUT):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None

    def connect(self) -> None:
        """Establish a TCP connection to the ESP32 command server."""
        if self._sock is not None:
            self.close()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        try:
            self._sock.connect((self.host, self.port))
            logger.info("Connected to ESP32 at %s:%d", self.host, self.port)
        except OSError as e:
            logger.error("Failed to connect to %s:%d: %s", self.host, self.port, e)
            self._close_socket()
            raise

    def close(self) -> None:
        """Close the TCP connection."""
        self._close_socket()

    def _close_socket(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def send_command(self, command: str) -> str:
        """
        Send a command and return the response.

        Args:
            command: One of "COLOR:<name>", "RGB:<r>,<g>,<b>", "OFF", "STATUS?"

        Returns:
            Response string from ESP32 (e.g. "OK", "ERR:*", "STATUS:active")

        Raises:
            ConnectionError: If not connected or connection fails.
        """
        if self._sock is None:
            self.connect()

        try:
            self._sock.sendall((command + "\n").encode("utf-8"))
            response = self._recv_line()
            logger.debug("Command '%s' -> '%s'", command, response.strip())
            return response.strip()
        except OSError as e:
            logger.error("Command '%s' failed: %s", command, e)
            self._close_socket()
            raise ConnectionError("ESP32 command failed: %s" % e)

    def _recv_line(self) -> str:
        """Read a newline-terminated response from the socket."""
        buffer = b""
        while True:
            try:
                chunk = self._sock.recv(1)
            except socket.timeout:
                break
            if not chunk:
                break
            buffer += chunk
            if chunk == b"\n":
                break
        return buffer.decode("utf-8", errors="replace")

    # ---- High-level convenience methods ----

    def set_color(self, color_name: str) -> str:
        """Set LED color by named color (e.g. 'blue', 'red', 'light_blue')."""
        return self.send_command("COLOR:%s" % color_name)

    def set_rgb(self, r: int, g: int, b: int) -> str:
        """Set LED color by RGB values (0-255 each)."""
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return self.send_command("RGB:%d,%d,%d" % (r, g, b))

    def set_rgb_tuple(self, rgb: Tuple[int, int, int]) -> str:
        """Set LED color from an (r, g, b) tuple."""
        return self.set_rgb(*rgb)

    def set_color_from_brand(self, brand: str, color_map: Optional[Dict[str, str]] = None) -> str:
        """
        Set LED color based on a brand name.

        Args:
            brand: Device brand (e.g. 'sony', 'microsoft', 'steam')
            color_map: Optional dict mapping brand -> color_name.
                       Defaults to BRAND_COLORS from colors module if available.

        Returns:
            Response string from ESP32.
        """
        if color_map is None:
            try:
                from colors import BRAND_COLORS
                color_map = BRAND_COLORS
            except ImportError:
                color_map = {}

        color_name = color_map.get(brand, "white")
        return self.set_color(color_name)

    def off(self) -> str:
        """Turn off the LED strip."""
        return self.send_command("OFF")

    def get_status(self) -> str:
        """Get ESP32 command server status."""
        return self.send_command("STATUS?")

    def mirror_local_color(self, color_name: str, color_map: Optional[Dict[str, str]] = None) -> None:
        """
        Convenience: convert named/hex/tuple color to RGB, then send to ESP32.
        Falls back to named color command if RGB conversion is not needed.

        Args:
            color_name: Named color, hex string (#RRGGBB or RRGGBB), or (r,g,b) tuple.
            color_map: Optional dict mapping brand -> color_name.
        """
        try:
            rgb = _to_rgb(color_name)
            self.set_rgb(*rgb)
        except Exception:
            self.set_color(color_name)


def get_esp32_client(config: Optional[Dict] = None, config_path: str = "config.json") -> Optional[ESP32Client]:
    """
    Factory function that creates an ESP32Client from a config dict or config file.
    Returns None if remote ESP32 is not configured.

    Args:
        config: A dict with an 'esp32_command' key.
        config_path: Path to config.json (used only if config is None).

    Returns:
        ESP32Client instance, or None if not configured.
    """
    if config is None:
        import json
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error("Could not load config from %s: %s", config_path, e)
            return None

    esp32_cfg = config.get("esp32_command", {})
    if not esp32_cfg.get("enabled", False):
        return None

    host = esp32_cfg.get("host", "192.168.1.50")
    port = esp32_cfg.get("port", DEFAULT_PORT)
    timeout = esp32_cfg.get("timeout", DEFAULT_TIMEOUT)

    logger.info("ESP32 remote client configured: %s:%d (timeout=%ds)", host, port, timeout)
    return ESP32Client(host=host, port=port, timeout=timeout)