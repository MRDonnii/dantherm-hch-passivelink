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


class ControllerLevelSelect(ControllerEntity, SelectEntity):
    _attr_options = ["1", "2", "3", "4", "5", "6"]

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "manual_level", "Ventilationsniveau")

    @property
    def current_option(self) -> str | None:
        value = self.coordinator.controller_state.get("effective_level")
        return str(value) if value is not None else None

    async def async_select_option(self, option: str) -> None:
        await self.async_command({"mode": "manual", "manual_level": int(option)})


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
        ControllerSelect(
            coordinator,
            "bypass",
            "Bypass",
            ["auto", "open", "closed"],
        ),
    ])
