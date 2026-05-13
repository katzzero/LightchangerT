import socket
from zeroconf import Zeroconf, ServiceBrowser


class SteamServiceListener:
    """Helper to browse for Steam services via mDNS."""
    def __init__(self, zonename="local."):
        self.zeroconf = Zeroconf()
        self.browser = None
        self.zonename = zonename
        self.found_services = {}

    def remove_all(self):
        if self.browser:
            self.browser.cancel()
        self.zeroconf.close()


class SteamDetector:
    def __init__(self, config):
        self.config = config.get('devices', {}).get('steam_detection', {})
        self.method = self.config.get('method', 'PORT_PROBE')
        self.port = self.config.get('port', 27036)
        self.hostname = self.config.get('mdns_hostname', 'steamdeck.local')

    def _probe_port(self, ip):
        """Tries to connect to the Steam port to verify active status."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                return s.connect_ex((ip, self.port)) == 0
        except Exception:
            return False

    def _resolve_mdns(self):
        """Attempts to resolve the Steam device via mDNS."""
        try:
            with Zeroconf() as zeroconf:
                infos = zeroconf.get_service_info('_http._tcp.local.', self.hostname, 1)
                if infos:
                    return socket.inet_nta(infos[0].addresses[0])
        except Exception:
            pass
        return None

    def resolve_mdns_multi(self, hostnames=None, timeout=2):
        """Attempt resolution of multiple mDNS hostnames.

        Args:
            hostnames: list of hostname strings (default from config)
            timeout: seconds to wait per hostname

        Returns:
            First resolved IP string, or None
        """
        if hostnames is None:
            hostnames = [
                self.config.get('mdns_hostname', 'steamdeck.local'),
                self.config.get('mdns_hostname_2', 'steam-pc.local'),
                self.config.get('mdns_hostname_3', 'steam-deck.local'),
            ]
        for hn in hostnames:
            try:
                with Zeroconf() as zeroconf:
                    infos = zeroconf.get_service_info('_http._tcp.local.', hn, timeout * 1000)
                    if infos and infos.addresses:
                        ip = socket.inet_nta(infos[0].addresses[0])
                        if ip:
                            return ip
            except Exception:
                pass
        return None

    def probe_ports_multi(self, ip, ports=None, retries=1):
        """Probe multiple ports on an IP with optional retries.

        Args:
            ip: target IP address
            ports: list of port numbers
            retries: number of times to retry each port

        Returns:
            True if any port responds, False otherwise
        """
        if ports is None:
            ports = [27036, 27016, 27017, 27015, 54985]

        for port in ports:
            for attempt in range(retries):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1)
                        if s.connect_ex((ip, port)) == 0:
                            return True
                except Exception:
                    pass
        return False

    def detect(self, network_ips, mode=None):
        """
        Detects Steam presence.
        network_ips: list of IPs currently active on network (from scanner/liveness)
        mode: override detection method ('PORT_PROBE', 'MDNS', 'HYBRID')

        Returns:
            dict with 'ip' and 'brand' keys if detected, None otherwise
        """
        method = mode if mode else self.method

        if method == "MDNS":
            ip = self._resolve_mdns()
            if ip and self._probe_port(ip):
                return {"ip": ip, "brand": "steam"}

        elif method == "PORT_PROBE":
            for ip in network_ips:
                if self._probe_port(ip):
                    return {"ip": ip, "brand": "steam"}

        elif method == "HYBRID":
            # Try mDNS first, fall back to port probe
            ip = self.resolve_mdns_multi()
            if ip and self._probe_port(ip):
                return {"ip": ip, "brand": "steam"}
            for ip in network_ips:
                if self._probe_port(ip):
                    return {"ip": ip, "brand": "steam"}

        return None


if __name__ == "__main__":
    import json
    with open("config.json", 'r') as f:
        config = json.load(f)
    detector = SteamDetector(config)
    result = detector.detect(["192.168.1.10"], mode="HYBRID")
    print("Steam detected:", result)