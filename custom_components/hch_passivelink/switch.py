"""Switch entities for the Raspberry Pi HCH controller."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .controller_entity import ControllerEntity


class FireplaceSwitch(ControllerEntity, SwitchEntity):
    _attr_icon = "mdi:fireplace"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "fireplace", "Pejsetilstand")

    @property
    def is_on(self) -> bool:
        return bool(self.controller_value)

    async def async_turn_on(self, **kwargs) -> None:
        await self.async_command({"fireplace": True})

    async def async_turn_off(self, **kwargs) -> None:
        await self.async_command({"fireplace": False})


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    if coordinator.controller_client is not None:
        async_add_entities([FireplaceSwitch(coordinator)])
