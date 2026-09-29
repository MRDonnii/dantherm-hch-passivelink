"""Which Home Assistant sensors the Pi controller can actually use.

The options flow only offers entities whose unit (and, where needed, device
class) the controller payload understands, so a user cannot pick e.g. a
battery percentage as room humidity or a EUR price as kr/kWh.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

# Room observations sent to Smart Auto.
KIND_TEMPERATURE = "temperature"
KIND_HUMIDITY = "humidity"
KIND_CO2 = "co2"
KIND_PM25 = "pm25"
# Leased signals shown in the Pi WebUI.
KIND_POWER = "power"
KIND_ENERGY = "energy"
KIND_PRICE = "price"

_PRICE_UNIT = re.compile(r"^(kr|dkk|øre|ore)/(kwh|mwh)$")


def _normalise_unit(unit: object) -> str:
    return str(unit or "").replace(" ", "").casefold()


def is_supported(kind: str, device_class: object, unit: object) -> bool:
    """Return True when a sensor with this device class and unit fits ``kind``."""
    device_class = str(device_class or "").casefold()
    unit = _normalise_unit(unit)
    if kind == KIND_TEMPERATURE:
        # The Pi expects °C; HA converts temperature sensors to the system unit.
        return unit == "°c"
    if kind == KIND_HUMIDITY:
        # "%" alone also matches batteries and valve positions.
        return device_class == "humidity" and unit == "%"
    if kind == KIND_CO2:
        return device_class == "carbon_dioxide" or (not device_class and unit == "ppm")
    if kind == KIND_PM25:
        return device_class == "pm25" and unit in {"µg/m³", "μg/m³"}
    if kind == KIND_POWER:
        return unit in {"w", "kw"}
    if kind == KIND_ENERGY:
        return unit in {"wh", "kwh", "mwh"}
    if kind == KIND_PRICE:
        return bool(_PRICE_UNIT.match(unit))
    return False


def supported_entity_ids(states: Iterable, kind: str, keep: object = None) -> list[str]:
    """Sensor entity ids suitable for ``kind``.

    ``keep`` (an already selected entity id) is always included so an
    existing choice stays visible even while its sensor is unavailable.
    """
    result = {
        state.entity_id
        for state in states
        if str(state.entity_id).startswith("sensor.")
        and is_supported(
            kind,
            state.attributes.get("device_class"),
            state.attributes.get("unit_of_measurement"),
        )
    }
    if keep:
        result.add(str(keep))
    return sorted(result)
