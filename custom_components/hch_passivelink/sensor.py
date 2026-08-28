"""Sensors for HCH PassiveLink."""

from dataclasses import dataclass
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

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
    Description(key="co2", translation_key="co2", native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION, device_class=SensorDeviceClass.CO2, state_class=SensorStateClass.MEASUREMENT),
    Description(key="afterheat_setpoint", translation_key="afterheat_setpoint", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="afterheat_room_setpoint", translation_key="afterheat_room_setpoint", icon="mdi:home-thermometer-outline"),
    Description(key="afterheat_extract_setpoint", translation_key="afterheat_extract_setpoint", icon="mdi:thermometer-off"),
    Description(key="extract_fan_rpm", translation_key="extract_fan_rpm", native_unit_of_measurement="rpm", state_class=SensorStateClass.MEASUREMENT),
    Description(key="supply_fan_rpm", translation_key="supply_fan_rpm", native_unit_of_measurement="rpm", state_class=SensorStateClass.MEASUREMENT),
    Description(key="extract_fan_percent", translation_key="extract_fan_percent", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="supply_fan_percent", translation_key="supply_fan_percent", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="heat_recovery_efficiency", translation_key="heat_recovery_efficiency", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, icon="mdi:heat-wave"),
    Description(key="supply_extract_delta", translation_key="supply_extract_delta", native_unit_of_measurement=UnitOfTemperature.CELSIUS, state_class=SensorStateClass.MEASUREMENT, icon="mdi:swap-vertical"),
    Description(key="outdoor_temperature_source", translation_key="outdoor_temperature_source", device_class=SensorDeviceClass.ENUM, options=["unit_sensor"], entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:thermometer-check"),
    Description(key="air_quality_index", translation_key="air_quality_index", device_class=SensorDeviceClass.ENUM, options=["good", "moderate", "poor"], icon="mdi:leaf"),
    Description(key="bus_frame_rate", translation_key="bus_frame_rate", native_unit_of_measurement="frames/min", state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:pulse"),
    Description(key="heat_recovery_status", translation_key="heat_recovery_status", device_class=SensorDeviceClass.ENUM, options=["good", "acceptable", "low"], icon="mdi:check-decagram-outline"),
    Description(key="heat_recovery_trend", translation_key="heat_recovery_trend", device_class=SensorDeviceClass.ENUM, options=["normal", "watch", "degraded"], icon="mdi:chart-timeline-variant"),
    Description(key="heat_recovery_reference", translation_key="heat_recovery_reference", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC),
    Description(key="heat_recovery_drop", translation_key="heat_recovery_drop", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC),
    Description(key="fan_control_delta", translation_key="fan_control_delta", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, icon="mdi:fan-plus"),
    Description(key="fan_rpm_delta", translation_key="fan_rpm_delta", native_unit_of_measurement="rpm", state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:fan-chevron-up"),
    Description(key="filter_last_change", translation_key="filter_last_change", entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:calendar-check"),
    Description(key="filter_change_count", translation_key="filter_change_count", entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:counter"),
    Description(key="operating_mode", translation_key="operating_mode", device_class=SensorDeviceClass.ENUM, options=["fireplace", "standby", "auto_or_boost", "manual_1", "manual_2", "manual_3", "auto_or_scheduled"]),
    Description(key="current_level", translation_key="current_level", device_class=SensorDeviceClass.ENUM, options=["off", "level_1", "level_2", "level_3", "boost"]),
    Description(key="filter_interval_days", translation_key="filter_interval_days", native_unit_of_measurement=UnitOfTime.DAYS, entity_category=EntityCategory.DIAGNOSTIC),
    Description(key="filter_days_remaining", translation_key="filter_days_remaining", native_unit_of_measurement=UnitOfTime.DAYS, entity_category=EntityCategory.DIAGNOSTIC),
    Description(key="filter_life_percent", translation_key="filter_life_percent", native_unit_of_measurement=PERCENTAGE, entity_category=EntityCategory.DIAGNOSTIC),
    Description(key="filter_status", translation_key="filter_status", device_class=SensorDeviceClass.ENUM, options=["ok", "change_soon", "overdue"], entity_category=EntityCategory.DIAGNOSTIC),
    Description(key="filter_source", translation_key="filter_source", device_class=SensorDeviceClass.ENUM, options=["hcp4_synchronized"], entity_category=EntityCategory.DIAGNOSTIC),
    Description(key="heat_recovery_raw", translation_key="heat_recovery_raw", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    Description(key="bypass_raw", translation_key="bypass_raw", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    Description(key="status_code", translation_key="status_code", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    Description(key="afterheat_raw", translation_key="afterheat_raw", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    Description(key="command_raw", translation_key="command_raw", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
)


class PassiveLinkSensor(PassiveLinkEntity, SensorEntity, RestoreEntity):
    def __init__(self, coordinator: PassiveLinkCoordinator, description: Description) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._restored_value = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self.key not in {
            "afterheat_setpoint",
            "afterheat_room_setpoint",
            "afterheat_extract_setpoint",
        } or self.key in self.coordinator.data:
            return
        state = await self.async_get_last_state()
        if state is None or state.state in {"unknown", "unavailable"}:
            return
        if self.key == "afterheat_setpoint":
            try:
                self._restored_value = float(state.state)
            except ValueError:
                return
        else:
            self._restored_value = state.state

    @property
    def available(self) -> bool:
        return super().available or self._restored_value is not None

    @property
    def native_value(self):
        value = self.coordinator.data.get(self.key, self._restored_value)
        if self.key in {"afterheat_room_setpoint", "afterheat_extract_setpoint"}:
            return "OFF" if value == "off" else f"{value} °C"
        return value


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities(PassiveLinkSensor(entry.runtime_data, description) for description in DESCRIPTIONS)
