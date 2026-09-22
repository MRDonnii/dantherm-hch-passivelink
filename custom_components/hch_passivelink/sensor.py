"""Sensors for HCH PassiveLink."""

from dataclasses import dataclass
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .controller_entity import ControllerEntity
from .coordinator import PassiveLinkCoordinator
from .entity import PI_KEYS, PREHEATER_KEYS, PassiveLinkEntity


@dataclass(frozen=True, kw_only=True)
class Description(SensorEntityDescription):
    pass


DESCRIPTIONS = (
    Description(key="outdoor_temperature", translation_key="outdoor_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="supply_temperature", translation_key="supply_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="extract_temperature", translation_key="extract_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="exhaust_temperature", translation_key="exhaust_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="co2", translation_key="co2", native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION, device_class=SensorDeviceClass.CO2, state_class=SensorStateClass.MEASUREMENT),
    Description(key="room_temperature", translation_key="room_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="relative_humidity", translation_key="relative_humidity", native_unit_of_measurement=PERCENTAGE, device_class=SensorDeviceClass.HUMIDITY, state_class=SensorStateClass.MEASUREMENT),
    Description(key="measured_relative_humidity", translation_key="measured_relative_humidity", native_unit_of_measurement=PERCENTAGE, device_class=SensorDeviceClass.HUMIDITY, state_class=SensorStateClass.MEASUREMENT),
    Description(key="afterheat_setpoint", translation_key="afterheat_setpoint", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="heating_coil_before_temperature", translation_key="heating_coil_before_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="heating_coil_after_temperature", translation_key="heating_coil_after_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="heating_coil_air_delta", translation_key="heating_coil_air_delta", native_unit_of_measurement=UnitOfTemperature.CELSIUS, state_class=SensorStateClass.MEASUREMENT, icon="mdi:delta"),
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
    Description(key="preheater_flow_temperature", translation_key="preheater_flow_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="preheater_return_temperature", translation_key="preheater_return_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    Description(key="preheater_water_delta", translation_key="preheater_water_delta", native_unit_of_measurement=UnitOfTemperature.CELSIUS, state_class=SensorStateClass.MEASUREMENT, icon="mdi:delta"),
    Description(key="preheater_activity", translation_key="preheater_activity", device_class=SensorDeviceClass.ENUM, options=["inactive", "low", "normal", "high"], icon="mdi:radiator"),
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
    Description(key="pi_cpu_temperature", translation_key="pi_cpu_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC),
    Description(key="pi_uptime_seconds", translation_key="pi_uptime_seconds", native_unit_of_measurement=UnitOfTime.SECONDS, device_class=SensorDeviceClass.DURATION, entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:timer-outline"),
    Description(key="pi_load_average_1m", translation_key="pi_load_average_1m", state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:speedometer"),
    Description(key="pi_memory_used_percent", translation_key="pi_memory_used_percent", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:memory"),
    Description(key="pi_disk_used_percent", translation_key="pi_disk_used_percent", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:harddisk"),
    Description(key="pi_core_voltage", translation_key="pi_core_voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC),
    Description(key="pi_model", translation_key="pi_model", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False, icon="mdi:raspberry-pi"),
    Description(key="pi_kernel_version", translation_key="pi_kernel_version", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False, icon="mdi:linux"),
)


CONTROLLER_SENSOR_SPECS = (
    ("active_master", "Aktiv master", None, "mdi:server-network"),
    ("effective_source", "Effektiv kilde", None, "mdi:source-branch"),
    ("effective_level", "Effektivt ventilationsniveau", None, "mdi:fan-speed-3"),
    ("effective_reason", "Effektiv årsag", None, "mdi:text-box-search-outline"),
    ("smart_demand", "Smart Auto behov", None, "mdi:brain"),
    ("smart_requested_level", "Smart Auto ønsket niveau", None, "mdi:fan-chevron-up"),
    ("smart_target_level", "Smart Auto aktivt målniveau", None, "mdi:target"),
    ("smart_controlling_room", "Smart Auto styrende rum", None, "mdi:home-lightning-bolt-outline"),
    ("smart_controlling_metric", "Smart Auto styrende måling", None, "mdi:gauge"),
    ("smart_max_co2", "Smart Auto højeste CO2", CONCENTRATION_PARTS_PER_MILLION, "mdi:molecule-co2"),
    ("smart_max_co2_room", "Smart Auto højeste CO2 rum", None, "mdi:home-alert-outline"),
    ("smart_max_rh", "Smart Auto højeste luftfugtighed", PERCENTAGE, "mdi:water-percent"),
    ("smart_max_rh_room", "Smart Auto højeste RH rum", None, "mdi:home-alert-outline"),
    ("smart_inputs_age_seconds", "Smart Auto inputalder", UnitOfTime.SECONDS, "mdi:timer-sand"),
    ("hardware_control_state", "Hardwarekontrolstatus", None, "mdi:shield-lock-outline"),
    ("hcp4_last_foreign_write_age", "Seneste HCP4-write", UnitOfTime.SECONDS, "mdi:timer-outline"),
    ("actual_fan_extract_percent", "Faktisk udsugning", PERCENTAGE, "mdi:fan"),
    ("actual_fan_supply_percent", "Faktisk indblæsning", PERCENTAGE, "mdi:fan"),
    ("actual_fan_extract_rpm", "Faktisk udsugning RPM", "rpm", "mdi:fan-speed-2"),
    ("actual_fan_supply_rpm", "Faktisk indblæsning RPM", "rpm", "mdi:fan-speed-2"),
    ("actual_afterheat_setpoint", "Faktisk eftervarme setpunkt", UnitOfTemperature.CELSIUS, "mdi:thermostat"),
    ("actual_supply_before_heater_temperature", "Luft før varmeflade", UnitOfTemperature.CELSIUS, "mdi:thermometer-low"),
    ("actual_supply_air_temperature", "Faktisk indblæsningstemperatur", UnitOfTemperature.CELSIUS, "mdi:thermometer-high"),
    ("actual_afterheat_frost_temperature", "Eftervarme frostføler", UnitOfTemperature.CELSIUS, "mdi:snowflake-thermometer"),
    ("actual_afterheat_valve_percent", "Eftervarme ventil", PERCENTAGE, "mdi:valve"),
    ("fireplace_remaining_seconds", "Pejsetid tilbage", UnitOfTime.SECONDS, "mdi:timer-outline"),
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


class ControllerStatusSensor(ControllerEntity, SensorEntity):
    def __init__(self, coordinator, key: str, name: str, unit, icon: str) -> None:
        super().__init__(coordinator, key, name)
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        return self.controller_value


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    entities = [
        PassiveLinkSensor(coordinator, description)
        for description in DESCRIPTIONS
        if description.key not in PREHEATER_KEYS | PI_KEYS
        or coordinator._auxiliary_client is not None
    ]
    if coordinator.controller_client is not None:
        entities.extend(
            ControllerStatusSensor(coordinator, key, name, unit, icon)
            for key, name, unit, icon in CONTROLLER_SENSOR_SPECS
        )
    async_add_entities(entities)
