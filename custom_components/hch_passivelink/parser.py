"""Passive Modbus RTU stream parser for Dantherm HCH5 MK1 + HAC1."""

from __future__ import annotations

import time
from collections.abc import Callable

KNOWN_SLAVES = {1, 0x40}
LEVEL_TARGETS = {
    "off": (0, 0), "level_1": (25, 13), "level_2": (55, 43),
    "level_3": (85, 73), "boost": (100, 88),
}


def crc16(data: bytes) -> int:
    """Return Modbus CRC-16."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


class RtuStreamParser:
    """Reassemble verified RTU frames from arbitrary TCP chunks."""

    def __init__(self, callback: Callable[[bytes], None]) -> None:
        self._callback = callback
        self._buffer = bytearray()

    def feed(self, data: bytes) -> None:
        self._buffer.extend(data)
        offset = 0
        while offset + 5 <= len(self._buffer):
            if self._buffer[offset] not in KNOWN_SLAVES:
                offset += 1
                continue
            function = self._buffer[offset + 1]
            lengths: list[int] = []
            if function in (3, 4):
                lengths.append(8)
                byte_count = self._buffer[offset + 2]
                if byte_count and byte_count <= 250 and byte_count % 2 == 0:
                    lengths.insert(0, 5 + byte_count)
            elif function == 6:
                lengths.append(8)
            elif function == 16:
                # A write-multiple-registers response is 8 bytes. A request
                # carries a byte count at offset 6 and is 9 + byte_count bytes.
                # Try the longer request first so its payload cannot be
                # discarded while passively observing both bus directions.
                if offset + 7 <= len(self._buffer):
                    byte_count = self._buffer[offset + 6]
                    if byte_count and byte_count <= 250 and byte_count % 2 == 0:
                        lengths.append(9 + byte_count)
                lengths.append(8)
            else:
                offset += 1
                continue
            frame = None
            for length in lengths:
                if offset + length > len(self._buffer):
                    continue
                candidate = bytes(self._buffer[offset : offset + length])
                if crc16(candidate[:-2]) == int.from_bytes(candidate[-2:], "little"):
                    frame = candidate
                    break
            if frame is None:
                if any(offset + length > len(self._buffer) for length in lengths):
                    break
                offset += 1
                continue
            self._callback(frame)
            offset += len(frame)
        if offset:
            del self._buffer[:offset]
        if len(self._buffer) > 1024:
            del self._buffer[:-16]


class DanthermDecoder:
    """Decode only values verified on the observed HCH5 MK1/HAC1 bus."""

    def __init__(self, on_update: Callable[[dict[str, object]], None]) -> None:
        self.data: dict[str, object] = {}
        self._on_update = on_update
        self._special_mode_flag: int | None = None
        self._last_explicit_command = 0.0
        self._night_transition_until = 0.0
        self._filter_command_until = 0.0
        self._pending_auto_until = 0.0
        self._pending_manual3_until = 0.0
        self._external_mode: str | None = None

    def _set(self, **values: object) -> None:
        changed = False
        for key, value in values.items():
            if self.data.get(key) != value:
                self.data[key] = value
                changed = True
        if changed:
            self._on_update(dict(self.data))

    def decode(self, frame: bytes) -> None:
        self._set(last_frame_monotonic=time.monotonic(), bus_traffic=True)
        slave, function = frame[0], frame[1]
        if slave == 0x40 and function == 16 and len(frame) >= 19:
            register = int.from_bytes(frame[2:4], "big")
            count = int.from_bytes(frame[4:6], "big")
            byte_count = frame[6]
            if register == 185 and count == 5 and byte_count == 10:
                values = [
                    int.from_bytes(frame[i:i + 2], "big")
                    for i in range(7, 17, 2)
                ]
                if values[0] & 0xFF == 1 and values[2] == 15 \
                        and values[1] % 256 == 0 \
                        and 5 <= values[1] // 256 <= 40:
                    self._set(afterheat_setpoint=values[1] // 256)
            elif register == 180 and count == 5 and byte_count == 10:
                values = [
                    int.from_bytes(frame[i:i + 2], "big")
                    for i in range(7, 17, 2)
                ]
                # Registers 182 and 183 are the two optional thermostat
                # setpoints. HCP4 writes 0x8000 when a setpoint is OFF.
                def thermostat_value(value: int) -> str:
                    return "off" if value == 0x8000 else str(value)

                if all(value == 0x8000 or 5 <= value <= 40 for value in values[2:4]):
                    self._set(
                        afterheat_room_setpoint=thermostat_value(values[2]),
                        afterheat_extract_setpoint=thermostat_value(values[3]),
                    )
            return
        if function in (3, 4) and len(frame) == 8:
            return
        if slave == 0x40 and function == 3 and len(frame) == 15 and frame[2] == 10:
            values = [int.from_bytes(frame[i:i + 2], "big") for i in range(3, 13, 2)]
            if values[:3] == [0x3000, 0x1100, 0] and 300 <= values[3] <= 10000:
                self._set(co2=values[3], hac1_connected=True)
            elif values[0] & 0xFF == 1 and values[2] == 15 and values[1] % 256 == 0 \
                    and 5 <= values[1] // 256 <= 40:
                self._set(afterheat_setpoint=values[1] // 256)
            elif values[4] == 0 and all(
                value == 0x8000 or 5 <= value <= 40 for value in values[2:4]
            ):
                # The regularly read register 180 block repeats the two
                # optional thermostat states, so OFF remains observable even
                # when PassiveLink missed the original HCP4 write request.
                self._set(
                    afterheat_room_setpoint=(
                        "off" if values[2] == 0x8000 else str(values[2])
                    ),
                    afterheat_extract_setpoint=(
                        "off" if values[3] == 0x8000 else str(values[3])
                    ),
                )
            return
        if slave != 1:
            return
        if function == 4:
            values = [int.from_bytes(frame[i:i + 2], "big") for i in range(3, len(frame) - 2, 2)]
            if len(values) == 4:
                self._set(**dict(zip(
                    ("outdoor_temperature", "supply_temperature", "extract_temperature", "exhaust_temperature"),
                    (value / 100.0 for value in values),
                )))
            elif len(values) == 5:
                raw, extract_rpm, supply_rpm, bypass_raw, status_code = values
                self._set(
                    heat_recovery_raw=raw, extract_fan_rpm=extract_rpm,
                    supply_fan_rpm=supply_rpm, bypass_raw=bypass_raw,
                    bypass_active=bypass_raw == 255, status_code=status_code,
                )
            return
        if function != 6:
            return
        register = int.from_bytes(frame[2:4], "big")
        value = int.from_bytes(frame[4:6], "big")
        now = time.monotonic()
        if register == 66:
            self._set(extract_fan_percent=value)
        elif register == 67:
            self._set(supply_fan_percent=value)
        elif register == 68:
            self._set(afterheat_raw=value)
        elif register == 76:
            self._special_mode_flag = value
        elif register == 143 and value:
            self._set(command_raw=value)
            if value in (189, 200, 205):
                self._last_explicit_command = now
            elif value == 172 and now - self._last_explicit_command > 10:
                self._night_transition_until = now + 2
            if value == 168:
                self._filter_command_until = now + 2
            if value == 172:
                self._pending_auto_until, self._pending_manual3_until = now + 5, 0
            elif value == 189:
                self._pending_manual3_until, self._pending_auto_until = now + 5, 0
        elif register == 168 and now <= self._filter_command_until and 3 <= value <= 12:
            self._set(filter_interval_days=value * 30)
        elif register == 146:
            self._set(hac1_connected=value == 1)
        self._update_mode(now)

    def _update_mode(self, now: float) -> None:
        extract = self.data.get("extract_fan_percent")
        supply = self.data.get("supply_fan_percent")
        if not isinstance(extract, int) or not isinstance(supply, int):
            return
        if now <= self._night_transition_until:
            self._set(night_mode=(extract, supply) == (25, 13))
            self._night_transition_until = 0
        manual3_distance = (extract - 85) ** 2 + (supply - 73) ** 2
        if now <= self._pending_manual3_until and manual3_distance <= 100:
            self._external_mode = "manual_3"
        if self._external_mode == "manual_3" and now <= self._pending_auto_until \
                and manual3_distance > 100:
            self._external_mode = "auto"
        fireplace = extract == 0 and supply > 0 and self._special_mode_flag == 1
        standby = extract == 0 and supply == 0 and self._special_mode_flag == 1
        current_level = min(
            LEVEL_TARGETS,
            key=lambda name: (extract - LEVEL_TARGETS[name][0]) ** 2
            + (supply - LEVEL_TARGETS[name][1]) ** 2,
        )
        if fireplace:
            mode = "fireplace"
        elif standby:
            mode = "standby"
        elif (extract, supply) == (100, 88):
            mode = "auto_or_boost"
        elif self._external_mode == "manual_3":
            mode = "manual_3"
        else:
            mode = {(25, 13): "manual_1", (55, 43): "manual_2", (85, 73): "manual_3"}.get(
                (extract, supply), "auto_or_scheduled"
            )
        self._set(
            fireplace=fireplace, standby=standby, current_level=current_level,
            operating_mode=mode,
        )
