import socket
import logging
import concurrent.futures
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener

logger = logging.getLogger(__name__)

class SteamServiceListener(ServiceListener):
    def __init__(self):
        self.services = []

    def add_service(self, zeroconf, type, name):
        try:
            info = zeroconf.get_service_info(type, name)
            if info:
                self.services.append(info)
        except Exception as e:
            logger.debug(f"Steam mDNS add error: {e}")

    def remove_service(self, zeroconf, type, name):
        pass

    def update_service(self, zeroconf, type, name):
        pass


class SteamDetector:
    STEAM_PORTS = [27036, 27016, 27017, 27015, 54985]
    
    STEAM_MDNS_NAMES = [
        "steamdeck",
        "steam-pc",
        "steam-deck",
        "valve",
    ]

    def __init__(self, config):
        self.config = config.get('devices', {}).get('steam_detection', {})
        self.method = self.config.get('method', 'PORT_PROBE')
        self.timeout = self.config.get('probe_timeout', 1)
        self.retries = self.config.get('retries', 2)
        self.hostname = self.config.get('mdns_hostname', 'steamdeck.local')
        self.port = self.config.get('port', 27036)

    def _probe_port(self, ip, port, timeout=1):
        """Try connecting to a single port on an IP."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                return s.connect_ex((ip, port)) == 0
        except (socket.timeout, socket.error, OSError):
            return False

    def _probe_ip(self, ip):
        """Probe multiple Steam ports on an IP, returns (ip, port) if any match."""
        for port in self.STEAM_PORTS:
            if self._probe_port(ip, port, self.timeout):
                return ip
        return None

    def probe_ips_concurrent(self, network_ips):
        """Probe all IPs concurrently for performance."""
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, len(network_ips) + 1)) as executor:
            futures = {executor.submit(self._probe_ip, ip): ip for ip in network_ips}
            for future in concurrent.futures.as_completed(futures, timeout=self.timeout * len(self.STEAM_PORTS) + 5):
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.debug(f"Port probe error: {e}")
        return results

    def _resolve_mdns(self):
        """Try to find Steam Deck via mDNS across multiple service types."""
        listener = SteamServiceListener()
        
        zeroconf_services = [
            '_http._tcp.local.',
            '_steamdeck._tcp.local.',
            '_valve._tcp.local.',
            '_ssh._tcp.local.',
        ]

        try:
            with Zeroconf() as zeroconf:
                browser = ServiceBrowser(zeroconf, zeroconf_services, listener=listener)
                
                # Wait for discovery
                import time
                time.sleep(2)
                browser.cancel()

                if listener.services:
                    logger.info(f"mDNS found {len(listener.services)} Steam-related services")
                    for info in listener.services:
                        if hasattr(info, 'addresses') and info.addresses:
                            ip_str = socket.inet_ntoa(info.addresses[0])
                            # Verify the resolved IP is actually responding on a Steam port
                            for port in self.STEAM_PORTS:
                                if self._probe_port(ip_str, port, 1):
                                    return {"ip": ip_str, "brand": "steam"}
        except Exception as e:
            logger.debug(f"mDNS discovery error: {e}")

        return None

    def detect(self, network_ips):
        """
        Detects Steam presence using configured method.
        Falls back across methods for reliability.
        
        network_ips: list of IPs currently active on network (from scanner/liveness)
        """
        detected = None

        if self.method == "MDNS":
            # Primary: mDNS discovery
            detected = self._resolve_mdns()
            if detected:
                logger.info(f"Steam Deck detected via mDNS: {detected['ip']}")
                return detected
            
            # Fallback: port probe on all IPs
            logger.info("mDNS failed, falling back to port probe")
            found_ips = self.probe_ips_concurrent(network_ips)
            if found_ips:
                return {"ip": found_ips[0], "brand": "steam"}

        elif self.method == "PORT_PROBE":
            # Primary: port probe with retries
            for attempt in range(self.retries):
                logger.debug(f"Steam port probe attempt {attempt + 1}/{self.retries}")
                found_ips = self.probe_ips_concurrent(network_ips)
                if found_ips:
                    detected = {"ip": found_ips[0], "brand": "steam"}
                    logger.info(f"Steam Deck detected via port probe: {detected['ip']}")
                    return detected

            logger.debug("Steam port probe found nothing")

        elif self.method == "HYBRID":
            # Try mDNS first, then port probe
            detected = self._resolve_mdns()
            if detected:
                logger.info(f"Steam Deck detected via mDNS: {detected['ip']}")
                return detected
            
            logger.info("mDNS failed, falling back to port probe")
            for attempt in range(self.retries):
                logger.debug(f"Steam port probe attempt {attempt + 1}/{self.retries}")
                found_ips = self.probe_ips_concurrent(network_ips)
                if found_ips:
                    detected = {"ip": found_ips[0], "brand": "steam"}
                    logger.info(f"Steam Deck detected via port probe: {detected['ip']}")
                    return detected

        return None
