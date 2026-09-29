"""Select entities for the Raspberry Pi HCH controller."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .controller_entity import ControllerEntity


class ControllerSelect(ControllerEntity, SelectEntity):
    def __init__(self, coordinator, key: str, name: str, options: list[str]) -> None:
        super().__init__(coordinator, key, name)
        self._attr_options = options

    @property
    def current_option(self) -> str | None:
        value = self.controller_value
        return str(value) if value is not None else None

    async def async_select_option(self, option: str) -> None:
        await self.async_command({self.key: option})


# OFF switches the unit off until it is switched on again (as in the WebUI).
LEVEL_OPTIONS = ["OFF", "1", "2", "3", "4", "5", "6"]


class ControllerLevelSelect(ControllerEntity, SelectEntity):
    _attr_options = LEVEL_OPTIONS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "manual_level", "Ventilationsniveau")

    @property
    def current_option(self) -> str | None:
        state = self.coordinator.controller_state
        if state.get("standby_active"):
            return "OFF"
        value = state.get("manual_level")
        return str(value) if value is not None else None

    async def async_select_option(self, option: str) -> None:
        if option == "OFF":
            await self.async_command({"standby_minutes": STANDBY_OPTIONS["Permanent"]})
            return
        patch = {"mode": "manual", "manual_level": int(option)}
        if self.coordinator.controller_state.get("standby_active"):
            patch["standby_minutes"] = 0
        await self.async_command(patch)


class FireplaceDurationSelect(ControllerEntity, SelectEntity):
    _attr_options = ["Slukket", "15 min", "30 min"]
    _attr_icon = "mdi:fireplace"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "fireplace_duration_minutes", "Pejsetid")

    @property
    def current_option(self) -> str | None:
        minutes = int(self.coordinator.controller_state.get("fireplace_duration_minutes") or 0)
        return {0: "Slukket", 15: "15 min", 30: "30 min"}.get(minutes, "Slukket")

    async def async_select_option(self, option: str) -> None:
        minutes = {"Slukket": 0, "15 min": 15, "30 min": 30}[option]
        await self.async_command({"fireplace_minutes": minutes})


BONFIRE_OPTIONS = {"Slukket": 0, "30 min": 30, "1 time": 60, "2 timer": 120, "3 timer": 180, "4 timer": 240}


class BonfireDurationSelect(ControllerEntity, SelectEntity):
    """Bonfire in the garden: fans at minimum for the chosen time, then back to normal."""

    _attr_options = list(BONFIRE_OPTIONS)
    _attr_icon = "mdi:campfire"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "bonfire_minutes", "Bål i haven")

    @property
    def available(self) -> bool:
        client = getattr(self.coordinator, "controller_client", None)
        return bool(client and client.connected and "bonfire_active" in self.coordinator.controller_state)

    @property
    def current_option(self) -> str | None:
        state = self.coordinator.controller_state
        if not state.get("bonfire_active"):
            return "Slukket"
        minutes = int(state.get("bonfire_minutes") or 0)
        return next((name for name, value in BONFIRE_OPTIONS.items() if value == minutes), None)

    async def async_select_option(self, option: str) -> None:
        await self.async_command({"bonfire_minutes": BONFIRE_OPTIONS[option]})


# -2 = until the next 07:00 on the Pi, -1 = until switched on again.
STANDBY_OPTIONS = {
    "Tændt": 0, "1 time": 60, "4 timer": 240, "8 timer": 480,
    "Til i morgen kl. 07": -2, "Permanent": -1,
}


class StandbyDurationSelect(ControllerEntity, SelectEntity):
    """Switch the unit off for a while, until tomorrow morning or permanently."""

    _attr_options = list(STANDBY_OPTIONS)
    _attr_icon = "mdi:power"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "standby_minutes", "Sluk anlæg")

    @property
    def available(self) -> bool:
        client = getattr(self.coordinator, "controller_client", None)
        return bool(client and client.connected and "standby_active" in self.coordinator.controller_state)

    @property
    def current_option(self) -> str | None:
        state = self.coordinator.controller_state
        if not state.get("standby_active"):
            return "Tændt"
        minutes = int(state.get("standby_minutes") or 0)
        return next((name for name, value in STANDBY_OPTIONS.items() if value == minutes), None)

    async def async_select_option(self, option: str) -> None:
        await self.async_command({"standby_minutes": STANDBY_OPTIONS[option]})


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    if coordinator.controller_client is None:
        return
    async_add_entities([
        ControllerSelect(
            coordinator,
            "mode",
            "Driftstilstand",
            ["local_auto", "smart_auto", "manual"],
        ),
        ControllerLevelSelect(coordinator),
        ControllerSelect(coordinator, "bypass", "Bypassstyring", ["off", "on"]),
        FireplaceDurationSelect(coordinator),
        BonfireDurationSelect(coordinator),
        StandbyDurationSelect(coordinator),
        ControllerSelect(coordinator, "balance_ratio_mode", "Luftbalance kanalforhold", ["auto", "fixed"]),
    ])
