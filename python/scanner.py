import json
import subprocess
import re
import logging

logger = logging.getLogger(__name__)


class NetworkScanner:
    def __init__(self, config_path="config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.subnet = self.config['network']['subnet']
        self.static_devices = self.config['devices']['static_list']
        self.oui_prefixes = self.config['devices']['oui_prefixes']

    def identify_brand(self, mac):
        """Matches a MAC address against OUI prefixes defined in config."""
        if not mac:
            return None

        for brand, prefixes in self.oui_prefixes.items():
            for prefix in prefixes:
                if mac.lower().startswith(prefix.lower()):
                    return brand
        return None

    def scan(self):
        """
        Performs a network scan.
        Uses static list + ARP table for device discovery.
        Honors network.detection_mode from config.
        """
        mode = self.config['network'].get('detection_mode', 'HYBRID')
        seen_ips = set()
        discovered = []

        # 1. Check Static List first
        if mode in ('HYBRID', 'STATIC_LIST'):
            for dev in self.static_devices:
                if dev['ip'] in seen_ips:
                    continue
                seen_ips.add(dev['ip'])
                discovered.append({
                    "ip": dev['ip'],
                    "mac": dev.get('mac', ''),
                    "brand": dev['brand']
                })

        # 2. Dynamic discovery via ARP table
        if mode in ('HYBRID', 'AUTO'):
            try:
                arp_output = subprocess.check_output(["arp", "-a"]).decode()
                lines = arp_output.split('\n')
                for line in lines:
                    mac_match = re.search(r"(?:[0-9a-fA-F]{1,2}[:-]){5}[0-9a-fA-F]{1,2}", line)
                    if not mac_match:
                        continue
                    mac = mac_match.group(0).lower()
                    ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                    if not ip_match:
                        continue
                    ip = ip_match.group(1)
                    if ip in seen_ips:
                        continue
                    brand = self.identify_brand(mac)
                    if brand:
                        seen_ips.add(ip)
                        discovered.append({"ip": ip, "mac": mac, "brand": brand})
            except Exception as e:
                logger.error(f"Scanning error: {e}")

        return discovered


if __name__ == "__main__":
    scanner = NetworkScanner()
    print("Scanning for gaming devices...")
    devices = scanner.scan()
    for d in devices:
        print(f"Found {d['brand']} at {d['ip']} [{d['mac']}]")