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

    def get_mac_address(self, ip):
        """Retrieves MAC address for a given IP using the arp command."""
        try:
            output = subprocess.check_output(["arp", "-a", ip], stderr=subprocess.STDOUT).decode()
            match = re.search(r"([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})", output)
            return match.group(0).lower() if match else None
        except subprocess.CalledProcessError:
            return None

    def identify_brand(self, mac):
        """Matches a MAC address against OUI prefixes defined in config."""
        if not mac:
            return None

        for brand, prefixes in self.oui_prefixes.items():
            for prefix in prefixes:
                if mac.startswith(prefix.lower()):
                    return brand
        return None

    def scan(self):
        """
        Performs a network scan.
        Uses static list + ARP table for device discovery.
        """
        seen_ips = set()
        discovered = []

        # 1. Check Static List first
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
        try:
            arp_output = subprocess.check_output(["arp", "-a"]).decode()
            lines = arp_output.split('\n')
            for line in lines:
                parts = re.findall(r"(\d+\.\d+\.\d+\.\d+).*?([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})", line)
                if parts:
                    ip = parts[0][0]
                    if ip in seen_ips:
                        continue
                    mac_match = re.search(r"([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})", line).group(0).lower()
                    brand = self.identify_brand(mac_match)
                    if brand:
                        seen_ips.add(ip)
                        discovered.append({"ip": ip, "mac": mac_match, "brand": brand})
        except Exception as e:
            logger.error(f"Scanning error: {e}")

        return discovered


if __name__ == "__main__":
    scanner = NetworkScanner()
    print("Scanning for gaming devices...")
    devices = scanner.scan()
    for d in devices:
        print(f"Found {d['brand']} at {d['ip']} [{d['mac']}]")