import json
import os
import tempfile
import threading
import logging
from pathlib import Path

CONFIG_FILE = "config.json"
logger = logging.getLogger(__name__)


class ConfigManager:
    _instance = None
    _lock = threading.Lock()
    _config_lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._config = None
                    cls._instance._path = CONFIG_FILE
        return cls._instance

    def load(self, config_path: str = None) -> dict:
        """Thread-safe config loading."""
        if config_path:
            self._path = config_path

        with self._config_lock:
            try:
                with open(self._path, 'r') as f:
                    self._config = json.load(f)
                logger.info(f"Configuration loaded from {self._path}")
                return self._config
            except FileNotFoundError:
                logger.error(f"Config file not found: {self._path}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in config file: {e}")
                raise

    def reload(self) -> dict:
        """Thread-safe config reload."""
        return self.load()

    def get(self, key: str = None, default=None):
        """Get config value by key path (e.g., 'network.scan_interval_seconds')."""
        with self._config_lock:
            if self._config is None:
                self.load()
            if key is None:
                return self._config
            keys = key.split('.')
            value = self._config
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    return default
            return value if value is not None else default

    def update(self, updates: dict):
        """Thread-safe config update with atomic writes."""
        with self._config_lock:
            if self._config is None:
                self.load()
            self._config.update(updates)
            # Atomic write: tempfile + os.replace to prevent corruption on crash
            dir_name = os.path.dirname(self._path) or '.'
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(self._config, f, indent=2)
                os.replace(tmp_path, self._path)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
            logger.info("Configuration updated")


def get_config_manager() -> ConfigManager:
    return ConfigManager()