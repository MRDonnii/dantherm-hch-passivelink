"""Fan entity for the Raspberry Pi HCH controller."""
from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .controller_entity import ControllerEntity

class HCHControllerFan(ControllerEntity, FanEntity):
    """Presets follow the Pi's step control: Boost is the highest step (4 or 6)."""

    _attr_supported_features = FanEntityFeature.PRESET_MODE
    _attr_icon = "mdi:fan"

    @property
    def preset_modes(self) -> list[str]:
        return ["Auto", "Smart Auto", *(f"Niveau {level}" for level in range(1, self.max_level)), "Boost"]

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
            return "Smart Auto"
        level = int(state.get("manual_level") or state.get("effective_level") or 0)
        if level == self.max_level:
            return "Boost"
        if 1 <= level < self.max_level:
            return f"Niveau {level}"
        return None

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == "Auto":
            await self.async_command({"mode": "local_auto"})
            return
        if preset_mode == "Smart Auto":
            await self.async_command({"mode": "smart_auto"})
            return
        if preset_mode == "Boost":
            level = self.max_level
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
