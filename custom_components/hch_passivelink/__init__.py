"""HCH PassiveLink integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_PORT
from .coordinator import PassiveLinkCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
PassiveLinkConfigEntry = ConfigEntry[PassiveLinkCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: PassiveLinkConfigEntry) -> bool:
    coordinator = PassiveLinkCoordinator(hass, entry.data[CONF_HOST], entry.data[CONF_PORT])
    entry.runtime_data = coordinator
    coordinator.task = entry.async_create_background_task(hass, coordinator.client.run(), "HCH PassiveLink TCP")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PassiveLinkConfigEntry) -> bool:
    await entry.runtime_data.client.stop()
    if entry.runtime_data.task:
        entry.runtime_data.task.cancel()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
