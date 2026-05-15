import subprocess
import platform
import logging
import json

logger = logging.getLogger(__name__)


class LivenessEngine:
    def __init__(self, config=None, config_path="config.json"):
        """
        Accept either a config dict or a config file path.
        Config is not used by is_alive but kept for consistent interface.
        """
        if config is not None:
            self.config = config
        else:
            try:
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                self.config = {}

    def is_alive(self, ip):
        """
        Checks if a device is actually awake using ICMP ping.
        Returns True if the device responds, False otherwise.
        Works correctly on Linux, macOS, and Windows.
        """
        system = platform.system().lower()
        if system == "windows":
            command = ["ping", "-n", "1", "-w", "1000", ip]
        elif system == "darwin":
            command = ["ping", "-c", "1", "-W", "2", ip]
        else:
            command = ["ping", "-c", "1", "-W", "2", ip]

        try:
            subprocess.check_call(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def check_multiple(self, ips):
        """
        Check liveness for multiple IPs.
        Returns a dict of {ip: bool}.
        """
        return {ip: self.is_alive(ip) for ip in ips}