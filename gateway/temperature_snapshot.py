"""Opt-in, fixed FC03 reads for HCH5 MK1/HAC1 diagnostics.

The established temperature snapshot remains registers 180..209. An optional,
independent probe can read registers 178/179 without affecting the HA snapshot.
Both operations are read-only FC03 requests and retain the existing busy-bus
and CRC guards.
"""
from __future__ import annotations

import logging
import time

LOGGER = logging.getLogger("passivelink-gateway")


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def frame(body: bytes) -> bytes:
    return body + crc16(body).to_bytes(2, "little")


# Production snapshot: unchanged from the known-good implementation.
REQUEST = frame(bytes.fromhex("400300b4001e"))

# Experimental read-only probe: slave 0x40, FC03, registers 178..179 only.
PROBE_REQUEST = frame(bytes.fromhex("400300b20002"))

_LAST_PROBE: tuple[int, int] | None = None


def _wait_for_quiet_bus(connection) -> bool:
    """Return True after 15 ms of silence, False if the bus stays busy."""
    deadline = time.monotonic() + 0.3
    quiet_since = time.monotonic()
    while time.monotonic() < deadline:
        waiting = connection.in_waiting
        if waiting:
            connection.read(waiting)
            quiet_since = time.monotonic()
        elif time.monotonic() - quiet_since >= 0.015:
            return True
        time.sleep(0.001)
    return False


def read_temperature_snapshot(connection) -> bytes | None:
    """Return paired 180..209 request/CRC-checked response, or skip safely."""
    if not _wait_for_quiet_bus(connection):
        return None

    connection.write(REQUEST)
    connection.flush()
    received = bytearray()
    deadline = time.monotonic() + 0.8
    while time.monotonic() < deadline:
        received.extend(connection.read(256))
        for offset in range(max(0, len(received) - 512), len(received) - 64):
            response = bytes(received[offset:offset + 65])
            if response[:3] == bytes([0x40, 0x03, 60]) and (
                crc16(response[:-2]) == int.from_bytes(response[-2:], "little")
            ):
                return REQUEST + response
        if len(received) > 1024:
            del received[:-128]
    return None


def read_probe_178_179(connection) -> tuple[int, int] | None:
    """Read and log raw HAC1 registers 178/179 without touching HA state.

    A timeout, exception-free non-response, or invalid CRC simply returns None.
    No synthetic snapshot is produced, so this probe cannot make the existing
    180..209 temperature path unavailable.
    """
    global _LAST_PROBE

    if not _wait_for_quiet_bus(connection):
        return None

    connection.write(PROBE_REQUEST)
    connection.flush()
    received = bytearray()
    deadline = time.monotonic() + 0.5
    while time.monotonic() < deadline:
        received.extend(connection.read(64))
        for offset in range(max(0, len(received) - 128), len(received) - 8):
            response = bytes(received[offset:offset + 9])
            if response[:3] == bytes([0x40, 0x03, 4]) and (
                crc16(response[:-2]) == int.from_bytes(response[-2:], "little")
            ):
                register_178 = int.from_bytes(response[3:5], "big")
                register_179 = int.from_bytes(response[5:7], "big")
                probe = (register_178, register_179)
                if probe != _LAST_PROBE:
                    LOGGER.info(
                        "HAC1 probe raw registers 178/179: "
                        "r178=%d (0x%04X, hi=%d, lo=%d), "
                        "r179=%d (0x%04X, hi=%d, lo=%d)",
                        register_178,
                        register_178,
                        register_178 >> 8,
                        register_178 & 0xFF,
                        register_179,
                        register_179,
                        register_179 >> 8,
                        register_179 & 0xFF,
                    )
                    _LAST_PROBE = probe
                return probe
        if len(received) > 256:
            del received[:-32]
    return None
