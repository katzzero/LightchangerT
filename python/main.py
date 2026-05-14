"""LightchangerT main entry point. Run from repo root:
    python3 python/main.py

Or from within python/:
    cd python && python3 main.py
"""
import time
import threading
import logging
import os
import sys

# Determine base directory (repo root) - works whether run from repo root or python/
if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == 'python':
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(BASE_DIR, 'python'))

from scanner import NetworkScanner
from liveness import LivenessEngine
from led_controller import get_led_controller
from colors import BRAND_COLORS as COLOR_MAP
from steam_detector import SteamDetector
from web_config import run_server
from esp32_client import get_esp32_client
from config_manager import get_config_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_CONFIG = os.path.join(BASE_DIR, "config.json")


class GameStateController:
    def __init__(self, config_path=None):
        self.cm = get_config_manager()
        config_path = config_path or DEFAULT_CONFIG
        self.config = self.cm.load(config_path)

        self.scanner = NetworkScanner(config_path)
        self.liveness = LivenessEngine(config_path)
        self.led = get_led_controller(self.config)
        self.steam = SteamDetector(self.config)

        self.color_map = self.config.get('colors', COLOR_MAP)

        # Remote ESP32 control (optional)
        self.esp32 = get_esp32_client(self.config)
        if self.esp32:
            logger.info(f"ESP32 remote control enabled: {self.esp32.host}:{self.esp32.port}")

        # Stores { brand: last_seen_timestamp }
        self.last_seen = {}

    def update(self):
        """Cycle: Scan -> Verify Liveness -> Update Priority -> Set LED"""
        candidates = self.scanner.scan()
        currently_active = []
        active_ips = []

        for device in candidates:
            if self.liveness.is_alive(device['ip']):
                brand = device['brand']
                self.last_seen[brand] = time.time()
                currently_active.append(brand)
                active_ips.append(device['ip'])

        steam_dev = self.steam.detect(active_ips)
        if steam_dev:
            self.last_seen['steam'] = time.time()
            currently_active.append('steam')

        if not currently_active:
            color = self.color_map.get('default', 'white')
            self.led.set_color(color)
            if self.esp32:
                self.esp32.set_color(color)
            return

        active_last_seen = {brand: ts for brand, ts in self.last_seen.items() if brand in currently_active}

        if active_last_seen:
            winner = max(active_last_seen, key=active_last_seen.get)
            color = self.color_map.get(winner, "white")
            self.led.set_color(color)
            if self.esp32:
                self.esp32.set_color(color)

    def run(self):
        web_enabled = self.cm.get('network.web_config_enabled', False)
        web_port = self.cm.get('network.web_config_port', 80)

        if web_enabled:
            logger.info(f"Starting Web Config Server on port {web_port}")
            web_thread = threading.Thread(target=run_server, args=(web_port,))
            web_thread.daemon = True
            web_thread.start()

        interval = self.cm.get('network.scan_interval_seconds', 30)
        logger.info(f"Starting LightchangerT service (Interval: {interval}s)")

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
            if self.esp32:
                self.esp32.off()


if __name__ == "__main__":
    app = GameStateController()
    app.run()