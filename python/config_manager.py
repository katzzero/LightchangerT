import json
import os
import tempfile
import threading
import logging
from pathlib import Path
from copy import deepcopy

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
                    cls._instance._running = False
        return cls._instance

    def load(self, config_path=None):
        """Thread-safe config loading."""
        if config_path:
            self._path = config_path

        with self._config_lock:
            try:
                with open(self._path, 'r') as f:
                    self._config = json.load(f)
                logger.info(f"Configuration loaded from {self._path}")
                return deepcopy(self._config)
            except FileNotFoundError:
                logger.error(f"Config file not found: {self._path}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in config file: {e}")
                raise

    def reload(self):
        """Thread-safe config reload."""
        return self.load()

    def get(self, key=None, default=None):
        """Get config value by key path (e.g., 'network.scan_interval_seconds')."""
        with self._config_lock:
            if self._config is None:
                self.load()
            if key is None:
                return deepcopy(self._config)
            keys = key.split('.')
            value = self._config
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    return default
            return deepcopy(value) if value is not None else default

    def update(self, updates):
        """Thread-safe config update with atomic writes and deep merge."""
        with self._config_lock:
            if self._config is None:
                self.load()
            self._deep_merge(self._config, updates)
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

    @staticmethod
    def _deep_merge(base, override):
        """Recursively merge override into base in-place."""
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                ConfigManager._deep_merge(base[k], v)
            else:
                base[k] = deepcopy(v)

    def watch(self, callback, interval=1.0):
        """
        Start a background thread that watches for config file changes
        and calls callback(config) when it changes.
        """
        import hashlib

        def _watch():
            last_hash = None
            while self._running:
                try:
                    with open(self._path, 'rb') as f:
                        current_hash = hashlib.sha256(f.read()).hexdigest()
                    if current_hash != last_hash:
                        last_hash = current_hash
                        with self._config_lock:
                            new_config = self.reload()
                        callback(deepcopy(new_config))
                except Exception:
                    pass
                import time
                time.sleep(interval)

        self._running = True
        self._watch_thread = threading.Thread(target=_watch, daemon=True)
        self._watch_thread.start()

    def stop_watch(self):
        """Stop the config file watcher."""
        self._running = False
        if hasattr(self, '_watch_thread'):
            self._watch_thread.join(timeout=2)


def get_config_manager():
    return ConfigManager()