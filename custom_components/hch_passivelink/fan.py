"""Fan entity for the Raspberry Pi HCH controller."""
from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .controller_entity import ControllerEntity

PRESETS = [
    "Auto",
    "Auto + Home Assistant",
    "Niveau 1",
    "Niveau 2",
    "Niveau 3",
    "Niveau 4",
    "Niveau 5",
    "Boost",
]


class HCHControllerFan(ControllerEntity, FanEntity):
    _attr_supported_features = FanEntityFeature.PRESET_MODE
    _attr_preset_modes = PRESETS
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "effective_level", "Ventilation")

    @property
    def is_on(self) -> bool:
        # This controller deliberately exposes no fan-off function.
        return self.available

    @property
    def preset_mode(self) -> str | None:
        state = self.coordinator.controller_state
        mode = state.get("mode")
        if mode == "local_auto":
            return "Auto"
        if mode == "smart_auto":
            return "Auto + Home Assistant"
        level = int(state.get("manual_level") or state.get("effective_level") or 0)
        if level == 6:
            return "Boost"
        if 1 <= level <= 5:
            return f"Niveau {level}"
        return None

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == "Auto":
            await self.async_command({"mode": "local_auto"})
            return
        if preset_mode == "Auto + Home Assistant":
            await self.async_command({"mode": "smart_auto"})
            return
        if preset_mode == "Boost":
            level = 6
        elif preset_mode.startswith("Niveau "):
            level = int(preset_mode.split()[-1])
        else:
            raise ValueError(f"Unsupported preset: {preset_mode}")
        await self.async_command({"mode": "manual", "manual_level": level})


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    if coordinator.controller_client is not None:
        async_add_entities([HCHControllerFan(coordinator)])
