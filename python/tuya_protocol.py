"""Native Tuya protocol implementation using stdlib + cryptography.

This module provides a minimal Tuya device controller without external
tinytuya dependency. Uses cryptography library for AES-128-ECB.
"""

import socket
import json
import struct
import time
import logging

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

TUYA_PORT_V33 = 6668
TUYA_PORT_V31 = 6667
TUYA_PREFIX = 0x55AA
PROTOCOL_VERSION_33 = 3
PROTOCOL_VERSION_31 = 1


def _derive_key(local_key: str) -> bytes:
    """Derive 16-byte AES key from Tuya local_key (hex string or raw)."""
    try:
        key_bytes = bytes.fromhex(local_key)
        if len(key_bytes) >= 16:
            return key_bytes[:16]
        return key_bytes.ljust(16, b'\x00')
    except ValueError:
        return local_key.encode('utf-8')[:16].ljust(16, b'\x00')


def _pkcs7_pad(data: bytes) -> bytes:
    """Apply PKCS7 padding (always adds padding, even when aligned)."""
    padding = 16 - (len(data) % 16)
    return data + bytes([padding] * padding)


def _pkcs7_unpad(data: bytes) -> bytes:
    """Remove PKCS7 padding with validation."""
    if len(data) == 0:
        return data
    padding = data[-1]
    if padding < 1 or padding > 16:
        return data
    for i in range(padding):
        if data[-(i + 1)] != padding:
            return data
    return data[:-padding]


class TuyaDevice:
    """Controls Tuya-compatible devices via local network protocol."""

    def __init__(self, device_id, address, local_key, version=3.3):
        self.device_id = device_id
        self.address = address
        self.local_key = local_key
        self.version = version
        self.port = TUYA_PORT_V33 if version >= 3.3 else TUYA_PORT_V31
        self._sock = None
        self._seq = 0
        self._aes_key = _derive_key(local_key)

    def _get_socket(self):
        """Get or create persistent socket connection."""
        if self._sock is None:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(5.0)
            try:
                self._sock.connect((self.address, self.port))
                logger.debug(f"Connected to Tuya device {self.address}:{self.port}")
            except Exception as e:
                logger.error(f"Failed to connect to Tuya device: {e}")
                self._sock = None
                raise
        return self._sock

    def _encrypt(self, data: bytes) -> bytes:
        """Encrypt data using AES-128-ECB with PKCS7 padding."""
        cipher = Cipher(algorithms.AES(self._aes_key), modes.ECB(), backend=default_backend())
        encryptor = cipher.encryptor()
        return encryptor.update(_pkcs7_pad(data)) + encryptor.finalize()

    def _decrypt(self, data: bytes) -> bytes:
        """Decrypt data using AES-128-ECB and remove PKCS7 padding."""
        cipher = Cipher(algorithms.AES(self._aes_key), modes.ECB(), backend=default_backend())
        decryptor = cipher.decryptor()
        return _pkcs7_unpad(decryptor.update(data) + decryptor.finalize())

    def _calculate_header_checksum(self, data: bytes) -> int:
        """Calculate header checksum (sum of first 14 bytes mod 256)."""
        return sum(data[:14]) % 256

    def generate_payload(self, command, data=None):
        """Generate a Tuya command payload.

        Args:
            command: Message type (e.g., 'CONTROL', 'STATUS')
            data: Dict of command parameters

        Returns:
            Raw message bytes ready to send
        """
        if command == 'CONTROL':
            msg_type = 0x0A
        elif command == 'STATUS':
            msg_type = 0x08
        elif command == 'DPS':
            msg_type = 0x09
        else:
            msg_type = 0x0A

        payload = json.dumps(data or {})
        encrypted = self._encrypt(payload.encode())

        header = bytearray(15)
        struct.pack_into('>I', header, 0, TUYA_PREFIX)
        struct.pack_into('>H', header, 4, len(encrypted) + 8)
        header[6] = 0x03 if self.version >= 3.3 else 0x01
        header[7] = msg_type
        struct.pack_into('>I', header, 8, self._seq)
        header[14] = self._calculate_header_checksum(bytes(header))

        self._seq = (self._seq + 1) % 65536
        return bytes(header) + encrypted

    def send_command(self, command, data=None):
        """Generate and send a command, returning the response.

        Args:
            command: Message type (e.g., 'CONTROL', 'STATUS')
            data: Dict of command parameters

        Returns:
            Decrypted response data dict, or None on failure
        """
        payload = self.generate_payload(command, data)
        return self._send_receive(payload)

    def _send_receive(self, payload):
        """Send command and receive response.

        Args:
            payload: Message bytes to send

        Returns:
            Decrypted response data dict, or None on failure
        """
        try:
            sock = self._get_socket()
            sock.send(payload)

            response = sock.recv(4096)
            if len(response) < 15:
                logger.warning(f"Tuya response too short: {len(response)} bytes")
                return None

            data_len = struct.unpack('>H', response[4:6])[0]
            if len(response) < data_len + 15:
                full_response = response
                while len(full_response) < data_len + 15:
                    more = sock.recv(4096)
                    if not more:
                        break
                    full_response += more
                response = full_response

            encrypted = response[15:15 + data_len - 8]
            decrypted = self._decrypt(encrypted)

            return json.loads(decrypted.decode())

        except socket.timeout:
            logger.error("Tuya device communication timeout")
            return None
        except Exception as e:
            logger.error(f"Tuya communication error: {e}")
            self._sock = None
            return None

    def close(self):
        """Close the socket connection."""
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None


CONTROL = 'CONTROL'
STATUS = 'STATUS'
DPS = 'DPS'
