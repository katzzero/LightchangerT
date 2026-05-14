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
import signal

import psutil

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

        self._running = True
        self._web_thread = None
        self._last_config_mtime = 0

        # Initialize subsystems with the loaded config
        self.scanner = NetworkScanner(self.config)
        self.liveness = LivenessEngine(self.config)
        self.led = get_led_controller(self.config)
        self.steam = SteamDetector(self.config)

        self.color_map = self.config.get('colors', COLOR_MAP)

        # Remote ESP32 control (optional)
        self.esp32 = get_esp32_client(self.config)
        if self.esp32:
            logger.info(f"ESP32 remote control enabled: {self.esp32.host}:{self.esp32.port}")

        # State tracking
        self.last_seen = {}
        self._missed_cycles = {}
        self._offline_threshold = self.config.get('network', {}).get('offline_threshold', 3)

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle SIGINT/SIGTERM gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self._running = False

    def _check_config_changes(self):
        """
        Periodically check if config.json was modified on disk.
        If changed, reload and reinitialize subsystems.
        """
        try:
            mtime = os.path.getmtime(DEFAULT_CONFIG)
            if mtime != self._last_config_mtime:
                logger.info("Config file changed on disk, reloading...")
                self.config = self.cm.reload()
                self._last_config_mtime = mtime

                # Reinitialize subsystems with new config
                self.scanner = NetworkScanner(self.config)
                self.liveness = LivenessEngine(self.config)
                self.steam = SteamDetector(self.config)
                self.color_map = self.config.get('colors', COLOR_MAP)
                self._offline_threshold = self.config.get('network', {}).get('offline_threshold', 3)

                # Reinitialize ESP32 client if config changed
                old_esp32 = self.esp32
                self.esp32 = get_esp32_client(self.config)
                if old_esp32 and old_esp32 is not self.esp32:
                    old_esp32.close()

                logger.info("Config reloaded successfully")
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning(f"Error checking config changes: {e}")

    def _cleanup_stale_brands(self, currently_active):
        for brand in list(self.last_seen):
            if brand in currently_active:
                self._missed_cycles[brand] = 0
            else:
                self._missed_cycles[brand] = self._missed_cycles.get(brand, 0) + 1
                if self._missed_cycles[brand] >= self._offline_threshold:
                    logger.info(f"Removing stale brand '{brand}' (offline for {self._missed_cycles[brand]} cycles)")
                    del self.last_seen[brand]
                    del self._missed_cycles[brand]

    def update(self):
        """Cycle: Scan -> Verify Liveness -> Update Priority -> Set LED"""
        # Use fresh config each cycle
        config = self.cm.get()
        if config:
            self.config = config

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

        self._cleanup_stale_brands(currently_active)

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
        web_user = self.cm.get('auth', {}).get('username', '')
        web_pass_hash = self.cm.get('auth', {}).get('password_hash', '')

        if web_enabled:
            logger.info(f"Starting Web Config Server on port {web_port}")
            self._web_thread = threading.Thread(
                target=run_server,
                args=(web_port, web_user or None, web_pass_hash or None),
                daemon=True
            )
            self._web_thread.start()

        interval = self.cm.get('network.scan_interval_seconds', 30)
        logger.info(f"Starting LightchangerT service (Interval: {interval}s)")

        self._last_config_mtime = os.path.getmtime(DEFAULT_CONFIG) if os.path.exists(DEFAULT_CONFIG) else 0
        last_config_check = 0

        try:
            while self._running:
                try:
                    # Check for config file changes every 10 cycles
                    if last_config_check >= 10:
                        self._check_config_changes()
                        last_config_check = 0
                    last_config_check += 1

                    self.update()
                except Exception as e:
                    logger.exception(f"Error in update cycle: {e}")

                # Sleep in small intervals to respond to signals faster
                for _ in range(int(interval * 2)):
                    if not self._running:
                        break
                    time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("Shutting down...")
            self.led.off()
            if self.esp32:
                try:
                    self.esp32.close()
                except Exception:
                    pass
            self.steam.close()
            logger.info("LightchangerT stopped.")


if __name__ == "__main__":
    app = GameStateController()
    app.run()