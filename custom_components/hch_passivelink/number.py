"""Number entities for Raspberry Pi HCH controller configuration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .controller_entity import ControllerEntity


@dataclass(frozen=True)
class NumberSpec:
    key: str
    name: str
    minimum: float
    maximum: float
    step: float
    unit: str | None = None
    icon: str | None = None


SPECS = (
    NumberSpec("rh_setpoint", "RH setpunkt", 25, 80, 1, PERCENTAGE, "mdi:water-percent"),
    NumberSpec("rh_hysteresis", "RH hysterese", 1, 10, 1, PERCENTAGE, "mdi:arrow-expand-vertical"),
    NumberSpec("co2_setpoint", "CO₂ setpunkt", 500, 2000, 50, "ppm", "mdi:molecule-co2"),
    NumberSpec("co2_hysteresis", "CO₂ hysterese", 25, 500, 25, "ppm", "mdi:arrow-expand-vertical"),
    NumberSpec("auto_step_rh", "RH pr. ventilationstrin", 2, 20, 1, PERCENTAGE, "mdi:stairs-up"),
    NumberSpec("auto_step_co2", "CO₂ pr. ventilationstrin", 50, 1000, 50, "ppm", "mdi:stairs-up"),
    NumberSpec("local_normal_level", "Auto normalniveau", 1, 6, 1, None, "mdi:fan-auto"),
    NumberSpec("local_min_level", "Auto minimumsniveau", 1, 6, 1, None, "mdi:fan-minus"),
    NumberSpec("local_max_level", "Auto maksimumsniveau", 1, 6, 1, None, "mdi:fan-plus"),
    NumberSpec("downshift_delay_seconds", "Nedreguleringsforsinkelse", 30, 3600, 30, UnitOfTime.SECONDS, "mdi:timer-sand"),
    NumberSpec("boost_hold_seconds", "Boost holdetid", 60, 3600, 60, UnitOfTime.SECONDS, "mdi:timer-outline"),
    NumberSpec("ha_timeout_seconds", "Home Assistant timeout", 60, 3600, 30, UnitOfTime.SECONDS, "mdi:lan-disconnect"),
)


class ControllerNumber(ControllerEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, spec: NumberSpec) -> None:
        super().__init__(coordinator, spec.key, spec.name)
        self._attr_native_min_value = spec.minimum
        self._attr_native_max_value = spec.maximum
        self._attr_native_step = spec.step
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_icon = spec.icon

    @property
    def native_value(self) -> float | None:
        value = self.controller_value
        return float(value) if isinstance(value, (int, float)) else None

    async def async_set_native_value(self, value: float) -> None:
        if self._attr_native_step >= 1:
            value = int(round(value))
        await self.async_command({self.key: value})


class FanProfileNumber(ControllerEntity, NumberEntity):
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_step = 1

    def __init__(self, coordinator, level: int, kind: str) -> None:
        key = f"level_{level}_{kind}"
        label = "Udsugning" if kind == "extract" else "Indblæsning"
        super().__init__(coordinator, key, f"Niveau {level} {label}")
        self.level = level
        self.kind = kind
        self._attr_icon = "mdi:fan-chevron-up" if kind == "extract" else "mdi:fan-chevron-down"
        if kind == "extract":
            self._attr_native_min_value = 11
            self._attr_native_max_value = 100
        else:
            self._attr_native_min_value = 10
            self._attr_native_max_value = 99

    @property
    def available(self) -> bool:
        client = getattr(self.coordinator, "controller_client", None)
        return bool(client and client.connected and self.coordinator.controller_state.get("profiles"))

    @property
    def native_value(self) -> float | None:
        profiles = self.coordinator.controller_state.get("profiles") or {}
        profile = profiles.get(str(self.level)) or profiles.get(self.level) or {}
        value = profile.get(self.kind)
        return float(value) if isinstance(value, (int, float)) else None

    async def async_set_native_value(self, value: float) -> None:
        await self.async_command({
            "profiles": {str(self.level): {self.kind: int(round(value))}}
        })


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    if coordinator.controller_client is None:
        return
    entities = [ControllerNumber(coordinator, spec) for spec in SPECS]
    entities.extend(
        FanProfileNumber(coordinator, level, kind)
        for level in range(1, 7)
        for kind in ("extract", "supply")
    )
    async_add_entities(entities)
