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

        # Reuse a single Zeroconf instance instead of creating one per call
        self._zeroconf = None

    def _get_zeroconf(self):
        """Lazily create and reuse a single Zeroconf instance."""
        if self._zeroconf is None:
            self._zeroconf = Zeroconf()
        return self._zeroconf

    def close(self):
        """Clean up the shared Zeroconf instance."""
        if self._zeroconf is not None:
            self._zeroconf.close()
            self._zeroconf = None

    def _probe_port(self, ip, ports=None):
        """Tries to connect to Steam port(s) to verify active status."""
        if ports is None:
            ports = [27036, 27016, 27017, 27015, 54985]

        for port in ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    if s.connect_ex((ip, port)) == 0:
                        return True
            except Exception:
                pass
        return False

    def _resolve_mdns(self, hostname=None, timeout=2):
        """Attempts to resolve the Steam device via mDNS."""
        if hostname is None:
            hostname = self.hostname
        try:
            zc = self._get_zeroconf()
            infos = zc.get_service_info('_http._tcp.local.', hostname, timeout * 1000)
            if infos and infos.addresses:
                return socket.inet_ntoa(infos.addresses[0])
        except Exception:
            pass
        return None

    def resolve_mdns_multi(self, hostnames=None, timeout=2):
        """Attempt resolution of multiple mDNS hostnames."""
        if hostnames is None:
            hostnames = [
                self.config.get('mdns_hostname', 'steamdeck.local'),
                self.config.get('mdns_hostname_2', 'steam-pc.local'),
                self.config.get('mdns_hostname_3', 'steam-deck.local'),
            ]
        for hn in hostnames:
            ip = self._resolve_mdns(hn, timeout)
            if ip:
                return ip
        return None

    def probe_ports_multi(self, ip, ports=None, retries=1):
        """Probe multiple ports on an IP with optional retries."""
        if ports is None:
            ports = [27036, 27016, 27017, 27015, 54985]

        for port in ports:
            for _ in range(retries):
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
            ip = self.resolve_mdns_multi()
            if ip and self._probe_port(ip):
                return {"ip": ip, "brand": "steam"}
            for ip in network_ips:
                if self._probe_port(ip):
                    return {"ip": ip, "brand": "steam"}

        return None