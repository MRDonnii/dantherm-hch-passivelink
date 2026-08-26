"""Sensors for HCH PassiveLink."""

from dataclasses import dataclass
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfConcentration, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PassiveLinkCoordinator
from .entity import PassiveLinkEntity


@dataclass(frozen=True, kw_only=True)
class Description(SensorEntityDescription):
    pass


DESCRIPTIONS = (
    Description(key="outdoor_temperature", translation_key="outdoor_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="supply_temperature", translation_key="supply_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="extract_temperature", translation_key="extract_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="exhaust_temperature", translation_key="exhaust_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="co2", translation_key="co2", native_unit_of_measurement=UnitOfConcentration.PARTS_PER_MILLION, device_class=SensorDeviceClass.CO2, state_class=SensorStateClass.MEASUREMENT),
    Description(key="afterheat_setpoint", translation_key="afterheat_setpoint", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="extract_fan_rpm", translation_key="extract_fan_rpm", native_unit_of_measurement="rpm", state_class=SensorStateClass.MEASUREMENT),
    Description(key="supply_fan_rpm", translation_key="supply_fan_rpm", native_unit_of_measurement="rpm", state_class=SensorStateClass.MEASUREMENT),
    Description(key="extract_fan_percent", translation_key="extract_fan_percent", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="supply_fan_percent", translation_key="supply_fan_percent", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="operating_mode", translation_key="operating_mode", device_class=SensorDeviceClass.ENUM, options=["fireplace", "standby", "auto_or_boost", "manual_1", "manual_2", "manual_3", "auto_or_scheduled"]),
    Description(key="current_level", translation_key="current_level", device_class=SensorDeviceClass.ENUM, options=["off", "level_1", "level_2", "level_3", "boost"]),
    Description(key="filter_interval_days", translation_key="filter_interval_days", native_unit_of_measurement=UnitOfTime.DAYS, entity_category=EntityCategory.DIAGNOSTIC),
    Description(key="heat_recovery_raw", translation_key="heat_recovery_raw", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    Description(key="bypass_raw", translation_key="bypass_raw", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    Description(key="status_code", translation_key="status_code", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    Description(key="afterheat_raw", translation_key="afterheat_raw", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    Description(key="command_raw", translation_key="command_raw", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
)


class PassiveLinkSensor(PassiveLinkEntity, SensorEntity):
    def __init__(self, coordinator: PassiveLinkCoordinator, description: Description) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.coordinator.data.get(self.key)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities(PassiveLinkSensor(entry.runtime_data, description) for description in DESCRIPTIONS)
