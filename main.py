import time
import threading
import logging
from scanner import NetworkScanner
from liveness import LivenessEngine
from led_controller import get_led_controller, COLOR_MAP
from steam_detector import SteamDetector
from web_config import run_server
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

class GameStateController:
    def __init__(self, config_path="config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.scanner = NetworkScanner(config_path)
        self.liveness = LivenessEngine(config_path)
        self.led = get_led_controller(self.config)
        self.steam = SteamDetector(self.config)

        self.color_map = self.config.get('colors', COLOR_MAP)

        # Stores { brand: last_seen_timestamp }
        self.last_seen = {}

    def update(self):
        """
        Cycle: Scan -> Verify Liveness -> Update Priority -> Set LED
        """
        # 1. Discover potential devices
        candidates = self.scanner.scan()
        
        currently_active = []

        # 2. Verify Liveness (to filter deep sleep)
        active_ips = []
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
            color = self.color_map.get('default', 'white')
            self.led.set_color(color)
            return

        # Filter last_seen to only include currently active devices
        active_last_seen = {brand: ts for brand, ts in self.last_seen.items() if brand in currently_active}

        # Find brand with the maximum timestamp among active devices
        if active_last_seen:
            winner = max(active_last_seen, key=active_last_seen.get)
            color = self.color_map.get(winner, "white")
            self.led.set_color(color)

    def run(self):
        # Start Web Config Server if enabled
        web_enabled = self.config['network'].get('web_config_enabled', False)
        web_port = self.config['network'].get('web_config_port', 80)

        if web_enabled:
            logger.info(f"Starting Web Config Server on port {web_port}")
            # Run in a separate thread so it doesn't block the main loop
            web_thread = threading.Thread(target=run_server, args=(web_port,))
            web_thread.daemon = True
            web_thread.start()

        interval = self.config['network'].get('scan_interval_seconds', 30)
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

if __name__ == "__main__":
    app = GameStateController()
    app.run()
