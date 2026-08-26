"""Base entity for HCH PassiveLink."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PassiveLinkCoordinator


class PassiveLinkEntity(CoordinatorEntity[PassiveLinkCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: PassiveLinkCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self.key = key
        self._attr_unique_id = f"hch5_mk1_hac1_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "hch5_mk1_hac1")},
            name="Dantherm HCH PassiveLink",
            manufacturer="Dantherm",
            model="HCH5 MK1 + HAC1",
        )

    @property
    def available(self) -> bool:
        return self.coordinator.available and self.key in self.coordinator.data
