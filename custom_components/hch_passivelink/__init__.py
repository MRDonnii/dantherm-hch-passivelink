"""HCH PassiveLink integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import issue_registry as ir

from .client import PassiveLinkClient, PassiveSerialClient
from .const import (
    CONF_CONNECTION_TYPE,
    CONF_HOST,
    CONF_PORT,
    CONF_SERIAL_PORT,
    CONF_FILTER_NOTIFY_DAYS,
    CONF_FILTER_NOTIFY_ENABLED,
    CONF_FILTER_NOTIFY_SERVICE,
    CONF_PREHEATER_SENSORS_ENABLED,
    CONF_PREHEATER_SENSOR_HOST,
    CONF_PREHEATER_SENSOR_PORT,
    CONF_PREHEATER_SWAP_SENSORS,
    DEFAULT_FILTER_NOTIFY_DAYS,
    DEFAULT_PREHEATER_SENSOR_PORT,
    CONNECTION_SERIAL,
    CONNECTION_TCP,
    DOMAIN,
)
from .auxiliary import AuxiliaryTemperatureClient
from .coordinator import (
    ISSUE_CONNECTION_LOST,
    ISSUE_HAC1_DISCONNECTED,
    PassiveLinkCoordinator,
)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]
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
        auxiliary_client=(
            AuxiliaryTemperatureClient(
                async_get_clientsession(hass),
                config.get(CONF_PREHEATER_SENSOR_HOST)
                or config.get(CONF_HOST, "127.0.0.1"),
                config.get(
                    CONF_PREHEATER_SENSOR_PORT, DEFAULT_PREHEATER_SENSOR_PORT
                ),
                swap_sensors=config.get(CONF_PREHEATER_SWAP_SENSORS, False),
            )
            if config.get(CONF_PREHEATER_SENSORS_ENABLED, False)
            else None
        ),
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
    ir.async_delete_issue(hass, DOMAIN, ISSUE_CONNECTION_LOST)
    ir.async_delete_issue(hass, DOMAIN, ISSUE_HAC1_DISCONNECTED)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
