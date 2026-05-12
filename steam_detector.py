import socket
from zeroconf import Zeroconf, ServiceBrowser

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

    def detect(self, network_ips):
        """
        Detects Steam presence.
        network_ips: list of IPs currently active on network (from scanner/liveness)
        """
        if self.method == "MDNS":
            ip = self._resolve_mdns()
            if ip:
                # Verify the resolved IP is actually responding
                if self._probe_port(ip):
                    return {"ip": ip, "brand": "steam"}
        
        elif self.method == "PORT_PROBE":
            # Check all active network devices for the Steam port
            for ip in network_ips:
                if self._probe_port(ip):
                    return {"ip": ip, "brand": "steam"}
        
        return None
