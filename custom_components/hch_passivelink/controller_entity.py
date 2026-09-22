"""Base entities for the Raspberry Pi HCH controller."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class ControllerEntity(CoordinatorEntity):
    """Entity backed by controller state while the Pi remains source of truth."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        self.key = key
        self._attr_name = name
        self._attr_unique_id = f"hch5_pi_controller_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "hch5_pi_controller")},
            name="Dantherm HCH5 controller",
            manufacturer="Dantherm / PassiveLink",
            model="Raspberry Pi controller",
            via_device=(DOMAIN, "hch5_mk1_hac1"),
        )

    @property
    def available(self) -> bool:
        client = getattr(self.coordinator, "controller_client", None)
        return bool(client and client.connected and self.key in self.coordinator.controller_state)

    @property
    def controller_value(self):
        return self.coordinator.controller_state.get(self.key)

    async def async_command(self, patch: dict[str, object]) -> None:
        await self.coordinator.async_controller_command(patch)
