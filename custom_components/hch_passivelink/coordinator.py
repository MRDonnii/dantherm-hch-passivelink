"""Coordinator for HCH PassiveLink."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client import PassiveLinkClient


class PassiveLinkCoordinator(DataUpdateCoordinator[dict[str, object]]):
    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        super().__init__(hass, logger=__import__("logging").getLogger(__name__), name="HCH PassiveLink")
        self.data = {}
        self.client = PassiveLinkClient(host, port, self.async_set_updated_data)
        self.host, self.port = host, port
        self.task = None

    @property
    def available(self) -> bool:
        return self.client.connected and bool(self.data)
