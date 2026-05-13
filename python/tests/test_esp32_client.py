"""Tests for esp32_client.py — ESP32Client class and factory."""
import os
import sys
import socket
import json
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from esp32_client import ESP32Client, get_esp32_client, DEFAULT_PORT


class MockServer:
    """Helper that manages a TCP echo server for testing."""

    def __init__(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(("127.0.0.1", 0))
        self.server_sock.listen(5)
        self.server_sock.settimeout(5)
        self.port = self.server_sock.getsockname()[1]
        self.received_commands = []
        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def _accept_loop(self):
        while self._running:
            try:
                conn, _ = self.server_sock.accept()
                conn.settimeout(2)
                self._handle_client(conn)
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle_client(self, conn):
        buffer = b""
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                buffer += data
                if b"\n" in buffer:
                    line = buffer.decode("utf-8").strip()
                    self.received_commands.append(line)
                    if line == "STATUS?":
                        conn.sendall(b"STATUS:active\n")
                    else:
                        conn.sendall(b"OK\n")
                    buffer = b""
        except socket.timeout:
            pass
        finally:
            conn.close()

    def stop(self):
        self._running = False
        try:
            self.server_sock.close()
        except OSError:
            pass


@pytest.fixture
def server():
    ms = MockServer()
    yield ms
    ms.stop()


class TestESP32Client:
    """Tests for ESP32Client class."""

    def test_init_default_port(self):
        client = ESP32Client("192.168.1.50")
        assert client.port == DEFAULT_PORT
        assert client.host == "192.168.1.50"

    def test_init_custom_port(self):
        client = ESP32Client("192.168.1.50", port=8888)
        assert client.port == 8888

    def test_init_custom_timeout(self):
        client = ESP32Client("192.168.1.50", timeout=10)
        assert client.timeout == 10

    def test_close_when_not_connected(self):
        client = ESP32Client("192.168.1.50")
        client.close()  # Should not raise

    def test_send_command_connects_if_needed(self, server):
        client = ESP32Client("127.0.0.1", port=server.port, timeout=2)
        response = client.send_command("COLOR:blue")
        assert response == "OK"
        assert "COLOR:blue" in server.received_commands
        client.close()

    def test_send_command_off(self, server):
        client = ESP32Client("127.0.0.1", port=server.port, timeout=2)
        response = client.send_command("OFF")
        assert response == "OK"
        assert "OFF" in server.received_commands
        client.close()

    def test_send_command_status(self, server):
        client = ESP32Client("127.0.0.1", port=server.port, timeout=2)
        response = client.send_command("STATUS?")
        assert response == "STATUS:active"
        assert "STATUS?" in server.received_commands
        client.close()

    def test_send_command_rgb(self, server):
        client = ESP32Client("127.0.0.1", port=server.port, timeout=2)
        response = client.send_command("RGB:255,128,0")
        assert response == "OK"
        assert "RGB:255,128,0" in server.received_commands
        client.close()

    def test_set_color(self, server):
        client = ESP32Client("127.0.0.1", port=server.port, timeout=2)
        response = client.set_color("red")
        assert response == "OK"
        assert "COLOR:red" in server.received_commands
        client.close()

    def test_set_rgb(self, server):
        client = ESP32Client("127.0.0.1", port=server.port, timeout=2)
        response = client.set_rgb(0, 255, 128)
        assert response == "OK"
        assert "RGB:0,255,128" in server.received_commands
        client.close()

    def test_off(self, server):
        client = ESP32Client("127.0.0.1", port=server.port, timeout=2)
        response = client.off()
        assert response == "OK"
        assert "OFF" in server.received_commands
        client.close()

    def test_get_status(self, server):
        client = ESP32Client("127.0.0.1", port=server.port, timeout=2)
        response = client.get_status()
        assert response == "STATUS:active"
        assert "STATUS?" in server.received_commands
        client.close()

    def test_send_command_newline_delimited(self, server):
        client = ESP32Client("127.0.0.1", port=server.port, timeout=2)
        client.send_command("COLOR:green")
        assert any("COLOR:green" in cmd for cmd in server.received_commands)
        client.close()

    def test_connect_explicit(self, server):
        client = ESP32Client("127.0.0.1", port=server.port, timeout=2)
        client.connect()
        assert client._sock is not None
        assert not client._sock._closed
        client.close()
        assert client._sock is None

    def test_double_close_safe(self, server):
        client = ESP32Client("127.0.0.1", port=server.port, timeout=2)
        client.connect()
        client.close()
        client.close()  # Should not raise

    def test_set_rgb_clamps_values(self, server):
        client = ESP32Client("127.0.0.1", port=server.port, timeout=2)
        client.set_rgb(300, -10, 500)
        assert any("RGB:255,0,255" in cmd for cmd in server.received_commands)
        client.close()

    def test_sequential_commands(self, server):
        """Multiple commands over one connection work correctly."""
        client = ESP32Client("127.0.0.1", port=server.port, timeout=2)
        r1 = client.send_command("COLOR:red")
        r2 = client.send_command("OFF")
        r3 = client.get_status()
        assert r1 == "OK"
        assert r2 == "OK"
        assert r3 == "STATUS:active"
        assert server.received_commands == ["COLOR:red", "OFF", "STATUS?"]
        client.close()


class TestESP32ClientFactory:
    """Tests for the get_esp32_client() factory function."""

    def test_returns_none_when_disabled(self):
        config = {"esp32_command": {"enabled": False}}
        client = get_esp32_client(config=config)
        assert client is None

    def test_returns_none_when_missing_key(self):
        config = {}
        client = get_esp32_client(config=config)
        assert client is None

    def test_creates_client_when_enabled(self, server):
        config = {
            "esp32_command": {
                "enabled": True,
                "host": "127.0.0.1",
                "port": server.port,
            }
        }
        client = get_esp32_client(config=config)
        assert client is not None
        assert client.host == "127.0.0.1"
        assert client.port == server.port

    def test_defaults_to_standard_port(self):
        config = {"esp32_command": {"enabled": True, "host": "192.168.1.50"}}
        client = get_esp32_client(config=config)
        assert client.port == DEFAULT_PORT

    def test_custom_timeout(self):
        config = {"esp32_command": {"enabled": True, "host": "192.168.1.50", "timeout": 20}}
        client = get_esp32_client(config=config)
        assert client.timeout == 20

    def test_file_config_loading(self, tmp_path):
        config_file = tmp_path / "test_config.json"
        config_file.write_text('{"esp32_command": {"enabled": false}}')
        client = get_esp32_client(config_path=str(config_file))
        assert client is None

    def test_file_config_missing_esp32_section(self, tmp_path):
        config_file = tmp_path / "test_config.json"
        config_file.write_text('{"network": {"scan_interval_seconds": 30}}')
        client = get_esp32_client(config_path=str(config_file))
        assert client is None