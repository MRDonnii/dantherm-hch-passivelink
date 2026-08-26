"""Binary sensors for HCH PassiveLink."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import PassiveLinkEntity

DESCRIPTIONS = (
    BinarySensorEntityDescription(key="bypass_active", translation_key="bypass_active", device_class=BinarySensorDeviceClass.OPENING),
    BinarySensorEntityDescription(key="fireplace", translation_key="fireplace"),
    BinarySensorEntityDescription(key="standby", translation_key="standby"),
    BinarySensorEntityDescription(key="night_mode", translation_key="night_mode"),
    BinarySensorEntityDescription(key="hac1_connected", translation_key="hac1_connected", device_class=BinarySensorDeviceClass.CONNECTIVITY, entity_category=EntityCategory.DIAGNOSTIC),
    BinarySensorEntityDescription(key="bus_traffic", translation_key="bus_traffic", device_class=BinarySensorDeviceClass.CONNECTIVITY, entity_category=EntityCategory.DIAGNOSTIC),
    BinarySensorEntityDescription(key="filter_alarm", translation_key="filter_alarm", device_class=BinarySensorDeviceClass.PROBLEM, entity_category=EntityCategory.DIAGNOSTIC),
)


class PassiveLinkBinarySensor(PassiveLinkEntity, BinarySensorEntity):
    def __init__(self, coordinator, description) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self):
        return bool(self.coordinator.data.get(self.key))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities(PassiveLinkBinarySensor(entry.runtime_data, description) for description in DESCRIPTIONS)
