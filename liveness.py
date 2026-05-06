import subprocess
import platform

class LivenessEngine:
    def __init__(self, config_path="config.json"):
        import json
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.threshold = self.config['network'].get('offline_threshold', 3)

    def is_alive(self, ip):
        """
        Checks if a device is actually awake using ICMP ping.
        Returns True if the device responds, False otherwise.
        """
        # Determine the correct ping flag based on OS
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", "-W", "1", ip] # -W 1 is timeout in seconds

        try:
            # We use stdout=subprocess.DEVNULL to keep the console clean
            subprocess.check_call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

if __name__ == "__main__":
    # Small test for the LivenessEngine
    engine = LivenessEngine()
    test_ip = "8.8.8.8" # Google DNS as a reliable test target
    print(f"Testing liveness for {test_ip}...")
    if engine.is_alive(test_ip):
        print(f"{test_ip} is ALIVE")
    else:
        print(f"{test_ip} is OFFLINE")
