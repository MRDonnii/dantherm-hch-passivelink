"""Switch entities for the Raspberry Pi HCH controller."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

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


class CoolingSwitch(ControllerEntity, SwitchEntity):
    _attr_icon = "mdi:snowflake"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "cooling_enabled", "Frikøling")

    @property
    def is_on(self) -> bool:
        return self.controller_value is True

    async def async_turn_on(self, **kwargs) -> None:
        await self.async_command({"cooling_enabled": True})

    async def async_turn_off(self, **kwargs) -> None:
        await self.async_command({"cooling_enabled": False})


class FireplaceSignalSwitch(ControllerEntity, RestoreEntity, SwitchEntity):
    """External fireplace signal for the Pi's automatic fireplace mode.

    Anything in HA (a stove sensor automation, a button, a voice command) can
    turn it on. The Pi only acts on it when Automatic fireplace mode is enabled
    in its WebUI, holds the unit's fireplace mode while it is on and runs the
    configured afterrun when it turns off.
    """

    _attr_icon = "mdi:fireplace"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "fireplace_auto_enabled", "Pejs automatik-signal")
        self._attr_unique_id = "hch5_pi_controller_fireplace_signal"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.fireplace_signal)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        state = self.coordinator.controller_state
        return {
            "automatik_aktiveret": state.get("fireplace_auto_enabled"),
            "automatik_aktiv": state.get("fireplace_auto_active"),
            "aarsag": state.get("fireplace_auto_reason"),
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state == "on":
            try:
                await self.coordinator.async_set_fireplace_signal(True)
            except Exception:  # noqa: BLE001 - Pi may still be starting
                # Keep the switch on; the minute renewal sends it once the Pi answers.
                self.coordinator.fireplace_signal = True
                self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_fireplace_signal(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_fireplace_signal(False)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    if coordinator.controller_client is not None:
        # The fireplace switch is retired: the Pejsetid select (Fra/15/30 min) is
        # the canonical control, so only the cooling switch is set up here.
        async_add_entities([CoolingSwitch(coordinator), FireplaceSignalSwitch(coordinator)])
