"""Coordinator for HCH PassiveLink."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

class PassiveLinkCoordinator(DataUpdateCoordinator[dict[str, object]]):
    def __init__(self, hass: HomeAssistant, client) -> None:
        super().__init__(hass, logger=__import__("logging").getLogger(__name__), name="Dantherm HCH PassiveLink")
        self.data = {}
        self.client = client
        self.task = None

    @property
    def available(self) -> bool:
        return self.client.connected and bool(self.data)
