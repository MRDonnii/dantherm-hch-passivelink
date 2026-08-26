"""HCH PassiveLink integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .client import PassiveLinkClient, PassiveSerialClient
from .const import (
    CONF_CONNECTION_TYPE,
    CONF_HOST,
    CONF_PORT,
    CONF_SERIAL_PORT,
    CONNECTION_SERIAL,
    CONNECTION_TCP,
)
from .coordinator import PassiveLinkCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
PassiveLinkConfigEntry = ConfigEntry[PassiveLinkCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: PassiveLinkConfigEntry) -> bool:
    connection_type = entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_TCP)
    if connection_type == CONNECTION_SERIAL:
        client = PassiveSerialClient(entry.data[CONF_SERIAL_PORT], lambda _: None)
        task_name = "Dantherm HCH PassiveLink USB-RS485"
    else:
        client = PassiveLinkClient(entry.data[CONF_HOST], entry.data[CONF_PORT], lambda _: None)
        task_name = "Dantherm HCH PassiveLink TCP"
    coordinator = PassiveLinkCoordinator(hass, client)
    client._update = coordinator.async_set_updated_data
    entry.runtime_data = coordinator
    coordinator.task = entry.async_create_background_task(hass, client.run(), task_name)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PassiveLinkConfigEntry) -> bool:
    await entry.runtime_data.client.stop()
    if entry.runtime_data.task:
        entry.runtime_data.task.cancel()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
