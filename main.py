import time
from scanner import NetworkScanner
from liveness import LivenessEngine
from led_controller import get_led_controller
from steam_detector import SteamDetector
import json

class GameStateController:
    def __init__(self, config_path="config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.scanner = NetworkScanner(config_path)
        self.liveness = LivenessEngine(config_path)
        self.led = get_led_controller(self.config)
        self.steam = SteamDetector(self.config)

        self.color_map = self.config.get('colors', {
            "sony": "blue",
            "microsoft": "green",
            "nintendo": "red",
            "steam": "light_blue",
            "nvidia": "light_green",
            "default": "white"
        })

        
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

        # Find brand with the maximum timestamp among active devices
        winner = max(self.last_seen, key=self.last_seen.get)
        # Only set color if the winner is actually in the active list for this cycle
        if winner in currently_active:
            color = self.color_map.get(winner, "white")
            self.led.set_color(color)

    def run(self):
        interval = self.config['network'].get('scan_interval_seconds', 30)
        print(f"Starting GameNetLight service... (Interval: {interval}s)")
        try:
            while True:
                self.update()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Shutting down...")
            self.led.off()

if __name__ == "__main__":
    app = GameStateController()
    app.run()
