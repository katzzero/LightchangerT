import time
import threading
import logging
import tempfile
import os
from scanner import NetworkScanner
from liveness import LivenessEngine
from led_controller import get_led_controller
from colors import BRAND_COLORS as COLOR_MAP
from steam_detector import SteamDetector
from web_config import run_server
from config_manager import ConfigManager
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class GameStateController:
    def __init__(self, config_path="config.json"):
        # Support both direct config dict and ConfigManager
        try:
            cm = ConfigManager()
            self.config = cm.get()
        except Exception:
            with open(config_path, 'r') as f:
                self.config = json.load(f)

        self.scanner = NetworkScanner() if self._config_exists() else None
        self.liveness = LivenessEngine()
        self.led = get_led_controller(self.config)
        self.steam = SteamDetector(self.config)

        self.color_map = self.config.get('colors', COLOR_MAP)

        self.last_seen = {}

        # Optional ESP32 remote mirror
        self.esp32_client = self._init_esp32_client()

    def _config_exists(self):
        try:
            with open("config.json", 'r') as f:
                json.load(f)
            return True
        except (FileNotFoundError, json.JSONDecodeError):
            return False

    def _init_esp32_client(self):
        """Initialize ESP32 remote client if configured."""
        try:
            from esp32_client import get_esp32_client
            return get_esp32_client(self.config)
        except ImportError:
            logger.warning("esp32_client not available, remote mirroring disabled")
            return None
        except Exception as e:
            logger.warning(f"Failed to init ESP32 client: {e}")
            return None

    def _set_esp32_color(self, rgb_tuple):
        """Mirror current color to remote ESP32."""
        if self.esp32_client:
            try:
                self.esp32_client.set_rgb(*rgb_tuple)
            except Exception as e:
                logger.warning(f"ESP32 remote update failed: {e}")

    def update(self):
        """
        Cycle: Scan -> Verify Liveness -> Update Priority -> Set LED
        """
        # 1. Discover potential devices
        if self.scanner:
            candidates = self.scanner.scan()
        else:
            candidates = []

        currently_active = []
        active_ips = []

        # 2. Verify Liveness (to filter deep sleep)
        for device in candidates:
            if self.liveness.is_alive(device['ip']):
                brand = device['brand']
                self.last_seen[brand] = time.time()
                currently_active.append(brand)
                active_ips.append(device['ip'])

        # 3. Check for Steam (special detection)
        steam_dev = self.steam.detect(active_ips)
        if steam_dev:
            self.last_seen['steam'] = time.time()
            currently_active.append('steam')

        # 4. Determine the "Last Online" winner
        if not currently_active:
            color_name = self.color_map.get('default', 'white')
            self.led.set_color(color_name)
            rgb = self._to_rgb_or_none(color_name)
            if rgb:
                self._set_esp32_color(rgb)
            return

        # Filter last_seen to only include currently active devices
        active_last_seen = {brand: ts for brand, ts in self.last_seen.items() if brand in currently_active}

        # Find brand with the maximum timestamp among active devices
        if active_last_seen:
            winner = max(active_last_seen, key=active_last_seen.get)
            color_name = self.color_map.get(winner, "white")
            self.led.set_color(color_name)
            rgb = self._to_rgb_or_none(color_name)
            if rgb:
                self._set_esp32_color(rgb)

    def _to_rgb_or_none(self, color_name):
        """Convert color name to RGB tuple, or None on failure."""
        try:
            from led_controller import _to_rgb
            return _to_rgb(color_name)
        except Exception:
            return None

    def run(self):
        # Start Web Config Server if enabled
        web_enabled = self.config.get('network', {}).get('web_config_enabled', False)
        web_port = self.config.get('network', {}).get('web_config_port', 80)

        if web_enabled:
            logger.info(f"Starting Web Config Server on port {web_port}")
            try:
                cm = ConfigManager()
                web_thread = threading.Thread(target=run_server, args=(web_port, cm))
                web_thread.daemon = True
                web_thread.start()
            except Exception as e:
                logger.warning(f"Could not start web config server: {e}")

        interval = self.config.get('network', {}).get('scan_interval_seconds', 30)
        logger.info(f"Starting LightchangerT service (Interval: {interval}s)")
        if self.esp32_client:
            logger.info(f"ESP32 remote mirror enabled -> {self.esp32_client.host}:{self.esp32_client.port}")

        try:
            while True:
                try:
                    self.update()
                except Exception as e:
                    logger.exception(f"Error in update cycle: {e}")
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.led.off()
            if self.esp32_client:
                self.esp32_client.off()


if __name__ == "__main__":
    app = GameStateController()
    app.run()