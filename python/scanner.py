import json
import os
import tempfile
import subprocess
import re
import platform
import logging

logger = logging.getLogger(__name__)


class NetworkScanner:
    def __init__(self, config=None, config_path="config.json"):
        """
        Accept either a config dict or a config file path (via ConfigManager).
        """
        if config is not None:
            self.config = config
        else:
            # Load via ConfigManager for consistency
            from config_manager import get_config_manager
            cm = get_config_manager()
            self.config = cm.load(config_path)
        self.subnet = self.config.get('network', {}).get('subnet', '192.168.1.0/24')
        self.static_devices = self.config.get('devices', {}).get('static_list', [])
        self.oui_prefixes = self.config.get('devices', {}).get('oui_prefixes', {})

    def identify_brand(self, mac):
        """Matches a MAC address against OUI prefixes defined in config."""
        if not mac:
            return None

        for brand, prefixes in self.oui_prefixes.items():
            for prefix in prefixes:
                if mac.lower().startswith(prefix.lower()):
                    return brand
        return None

    def _parse_arp_linux(self):
        """Parse ARP table on Linux."""
        entries = []
        try:
            output = subprocess.check_output(["arp", "-n"], timeout=10).decode()
            for line in output.split('\n'):
                parts = line.split()
                if len(parts) >= 4 and re.match(r'^\d+\.\d+\.\d+\.\d+$', parts[0]):
                    entries.append({"ip": parts[0], "mac": parts[3]})
        except Exception as e:
            logger.warning(f"ARP scan (Linux) failed: {e}")
        return entries

    def _parse_arp_darwin(self):
        """Parse ARP table on macOS."""
        entries = []
        try:
            output = subprocess.check_output(["arp", "-an"], timeout=10).decode()
            for line in output.split('\n'):
                ip_match = re.search(r'\((\d+\.\d+\.\d+\.\d+)\)', line)
                mac_match = re.search(r'((?:[0-9a-fA-F]{1,2}:){5}[0-9a-fA-F]{1,2})', line)
                if ip_match and mac_match:
                    entries.append({"ip": ip_match.group(1), "mac": mac_match.group(1)})
        except Exception as e:
            logger.warning(f"ARP scan (macOS) failed: {e}")
        return entries

    def _parse_arp_windows(self):
        """Parse ARP table on Windows."""
        entries = []
        try:
            output = subprocess.check_output(["arp", "-a"], timeout=10).decode('cp1252')
            in_table = False
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith('Interface:'):
                    in_table = True
                    continue
                if in_table and line:
                    parts = line.split()
                    if len(parts) >= 2 and re.match(r'^\d+\.\d+\.\d+\.\d+$', parts[0]):
                        mac = parts[1] if len(parts) > 1 else ""
                        if mac != "ff-ff-ff-ff-ff-ff":
                            entries.append({"ip": parts[0], "mac": mac})
                elif in_table and not line:
                    in_table = False
        except Exception as e:
            logger.warning(f"ARP scan (Windows) failed: {e}")
        return entries

    def _dynamic_scan(self):
        """Scan the network via ARP table based on the current platform."""
        system = platform.system().lower()
        if system == "darwin":
            return self._parse_arp_darwin()
        elif system == "windows":
            return self._parse_arp_windows()
        else:
            return self._parse_arp_linux()

    def scan(self):
        """
        Performs a network scan.
        Uses static list + ARP table (platform-aware) for device discovery.
        Honors network.detection_mode from config.
        """
        mode = self.config.get('network', {}).get('detection_mode', 'HYBRID')
        seen_ips = set()
        discovered = []

        # 1. Check Static List first
        if mode in ('HYBRID', 'STATIC_LIST'):
            for dev in self.static_devices:
                if dev.get('ip') in seen_ips:
                    continue
                seen_ips.add(dev.get('ip'))
                discovered.append({
                    "ip": dev.get('ip', ''),
                    "mac": dev.get('mac', ''),
                    "brand": dev.get('brand', '')
                })

        # 2. Dynamic discovery via ARP table
        if mode in ('HYBRID', 'AUTO'):
            arp_entries = self._dynamic_scan()
            for entry in arp_entries:
                ip = entry.get('ip', '')
                mac = entry.get('mac', '')
                if ip in seen_ips:
                    continue
                brand = self.identify_brand(mac)
                if brand:
                    seen_ips.add(ip)
                    discovered.append({
                        "ip": ip,
                        "mac": mac,
                        "brand": brand
                    })

        return discovered