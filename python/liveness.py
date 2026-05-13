import subprocess
import platform
import logging

logger = logging.getLogger(__name__)


class LivenessEngine:
    def __init__(self, config_path="config.json"):
        import json
        with open(config_path, 'r') as f:
            self.config = json.load(f)

    def is_alive(self, ip):
        """
        Checks if a device is actually awake using ICMP ping.
        Returns True if the device responds, False otherwise.
        """
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", "-W", "1", ip]

        try:
            subprocess.check_call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False


if __name__ == "__main__":
    engine = LivenessEngine()
    test_ip = "8.8.8.8"
    print(f"Testing liveness for {test_ip}...")
    if engine.is_alive(test_ip):
        print(f"{test_ip} is ALIVE")
    else:
        print(f"{test_ip} is OFFLINE")