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
    CONF_FILTER_NOTIFY_DAYS,
    CONF_FILTER_NOTIFY_ENABLED,
    CONF_FILTER_NOTIFY_SERVICE,
    DEFAULT_FILTER_NOTIFY_DAYS,
    CONNECTION_SERIAL,
    CONNECTION_TCP,
)
from .coordinator import PassiveLinkCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
PassiveLinkConfigEntry = ConfigEntry[PassiveLinkCoordinator]


async def _async_reload_entry(hass: HomeAssistant, entry: PassiveLinkConfigEntry) -> None:
    """Reload after connection options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: PassiveLinkConfigEntry) -> bool:
    config = {**entry.data, **entry.options}
    connection_type = config.get(CONF_CONNECTION_TYPE, CONNECTION_TCP)
    if connection_type == CONNECTION_SERIAL:
        client = PassiveSerialClient(config[CONF_SERIAL_PORT], lambda _: None)
        task_name = "Dantherm HCH PassiveLink USB-RS485"
    else:
        client = PassiveLinkClient(config[CONF_HOST], config[CONF_PORT], lambda _: None)
        task_name = "Dantherm HCH PassiveLink TCP"
    coordinator = PassiveLinkCoordinator(
        hass,
        client,
        entry.entry_id,
        notify_enabled=config.get(CONF_FILTER_NOTIFY_ENABLED, True),
        notify_days=config.get(CONF_FILTER_NOTIFY_DAYS, DEFAULT_FILTER_NOTIFY_DAYS),
        notify_service=config.get(CONF_FILTER_NOTIFY_SERVICE, ""),
    )
    await coordinator.async_load_filter_state()
    client.set_update_callback(coordinator.async_handle_update)
    entry.runtime_data = coordinator
    coordinator.task = entry.async_create_background_task(hass, client.run(), task_name)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PassiveLinkConfigEntry) -> bool:
    await entry.runtime_data.client.stop()
    await entry.runtime_data.async_shutdown()
    if entry.runtime_data.task:
        entry.runtime_data.task.cancel()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
