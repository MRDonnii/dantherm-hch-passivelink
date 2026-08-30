"""Opt-in, fixed FC03 temperature snapshot for HCH5 MK1/HAC1.

This sends a read request on RS485, never a register-write command. Enable only
on a verified installation; the default gateway remains completely passive.
"""
import time


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def frame(body: bytes) -> bytes:
    return body + crc16(body).to_bytes(2, "little")


REQUEST = frame(bytes.fromhex("400300b4001e"))


def read_temperature_snapshot(connection) -> bytes | None:
    """Return paired request/CRC-checked response, or skip a busy/failed bus.

    Called by the serial owner only, with a short serial read timeout. Registers
    180..209 contain T1..T5 at offsets 0..4 and T2AH/TFAH at offsets 25/26.
    Inter-register gaps are read but are not interpreted or written.
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
        for offset in range(max(0, len(received) - 512), len(received) - 64):
            response = bytes(received[offset:offset + 65])
            if response[:3] == bytes([64, 3, 60]) and (
                crc16(response[:-2]) == int.from_bytes(response[-2:], "little")
            ):
                return REQUEST + response
        if len(received) > 1024:
            del received[:-128]
    return None
