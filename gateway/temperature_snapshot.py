"""Opt-in, fixed FC03 temperature snapshot for HCH5 MK1/HAC1.

This sends a read request on RS485, never a register-write command. Enable only
on a verified installation; the default gateway remains completely passive.

The hardware probe reads registers 178..209 so the two words immediately before
the verified T1..T5 block can be observed safely. Registers 178/179 are logged
raw only; Home Assistant still receives the established 180..209 snapshot shape.
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


# Actual read sent on RS485: slave 0x40, FC03, registers 178..209 (32 words).
REQUEST = frame(bytes.fromhex("400300b20020"))

# Keep the TCP-facing snapshot format unchanged for the existing HA parser.
LEGACY_REQUEST = frame(bytes.fromhex("400300b4001e"))

_LAST_PROBE: tuple[int, int] | None = None


def _normalise_extended_snapshot(response: bytes) -> bytes:
    """Log registers 178/179 and return the established 180..209 snapshot."""
    global _LAST_PROBE

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

    # Extended payload is 64 bytes for registers 178..209. Drop the first
    # four bytes (178/179), then rebuild a valid 60-byte FC03 response for
    # registers 180..209 so no HA integration/parser change is needed yet.
    legacy_payload = response[7:67]
    legacy_response = frame(bytes([0x40, 0x03, 60]) + legacy_payload)
    return LEGACY_REQUEST + legacy_response


def read_temperature_snapshot(connection) -> bytes | None:
    """Return a compatible snapshot, or skip a busy/failed bus.

    Called by the serial owner only, with a short serial read timeout. The
    actual read covers registers 178..209. Verified data remains at the same
    physical addresses: T1..T5 are 180..184, T2AH/TFAH are 205/206, and 209 is
    the afterheat flag. Registers 178/179 are probe-only and never interpreted.
    """
    deadline = time.monotonic() + 0.3
    quiet_since = time.monotonic()
    while time.monotonic() < deadline:
        waiting = connection.in_waiting
        if waiting:
            connection.read(waiting)
            quiet_since = time.monotonic()
        elif time.monotonic() - quiet_since >= 0.015:
            break
        time.sleep(0.001)
    else:
        return None

    connection.write(REQUEST)
    connection.flush()
    received = bytearray()
    deadline = time.monotonic() + 0.8
    while time.monotonic() < deadline:
        received.extend(connection.read(256))

        # Expected response to the 32-register probe: 64 data bytes + header/CRC.
        for offset in range(max(0, len(received) - 512), len(received) - 68):
            response = bytes(received[offset:offset + 69])
            if response[:3] == bytes([0x40, 0x03, 64]) and (
                crc16(response[:-2]) == int.from_bytes(response[-2:], "little")
            ):
                return _normalise_extended_snapshot(response)

        # Defensive compatibility with the previous 180..209 response shape.
        # This also keeps older test fixtures valid while the hardware probe is
        # evaluated; it does not cause any extra RS485 transmission.
        for offset in range(max(0, len(received) - 512), len(received) - 64):
            response = bytes(received[offset:offset + 65])
            if response[:3] == bytes([0x40, 0x03, 60]) and (
                crc16(response[:-2]) == int.from_bytes(response[-2:], "little")
            ):
                return LEGACY_REQUEST + response

        if len(received) > 1024:
            del received[:-128]
    return None
