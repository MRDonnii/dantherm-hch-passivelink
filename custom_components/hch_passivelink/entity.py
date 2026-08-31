"""Base entity for HCH PassiveLink."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PassiveLinkCoordinator

AFTERHEAT_KEYS = {
    "afterheat_setpoint",
    "afterheat_room_setpoint",
    "afterheat_extract_setpoint",
    "afterheat_supply_setpoint",
    "afterheat_temperature",
    "heating_coil_before_temperature",
    "heating_coil_after_temperature",
    "heating_coil_air_delta",
    "afterheat_active",
    "afterheat_raw",
}
INDOOR_CLIMATE_KEYS = {
    "co2",
    "room_temperature",
    "relative_humidity",
    "air_quality",
    "air_quality_index",
}
FILTER_KEYS = {
    "filter_interval_days",
    "filter_days_remaining",
    "filter_life_percent",
    "filter_status",
    "filter_alarm",
    "filter_source",
    "filter_reset",
}
PREHEATER_KEYS = {
    "preheater_flow_temperature",
    "preheater_return_temperature",
    "preheater_water_delta",
    "preheater_activity",
    "preheater_sensor_connected",
}
ALARM_KEYS = {
    "extract_fan_fault", "supply_fan_fault", "outdoor_temperature_sensor_fault",
    "supply_temperature_sensor_fault", "extract_temperature_sensor_fault",
    "exhaust_temperature_sensor_fault", "room_temperature_sensor_fault",
    "outdoor_temperature_low", "supply_temperature_low", "fire_temperature_alarm",
}


class PassiveLinkEntity(CoordinatorEntity[PassiveLinkCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: PassiveLinkCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self.key = key
        self._attr_unique_id = f"hch5_mk1_hac1_{key}"
        if key in INDOOR_CLIMATE_KEYS:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, "hch5_mk1_hac1_indoor_climate")},
                name="Indeklima",
                manufacturer="Dantherm",
                model="HAC1 indeklimasensor",
                via_device=(DOMAIN, "hch5_mk1_hac1"),
            )
        elif key in AFTERHEAT_KEYS or key in PREHEATER_KEYS:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, "hch5_mk1_hac1_afterheat")},
                name="Eftervarme",
                manufacturer="Dantherm",
                model="HAC1 eftervarme",
                via_device=(DOMAIN, "hch5_mk1_hac1"),
            )
        elif key in FILTER_KEYS:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, "hch5_mk1_filter")},
                name="Filter",
                manufacturer="Dantherm",
                model="HCH5 filtertimer",
                via_device=(DOMAIN, "hch5_mk1_hac1"),
            )
        elif key in ALARM_KEYS:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, "hch5_mk1_hac1_alarms")},
                name="Alarmer",
                manufacturer="Dantherm",
                model="HCH5 derived fault monitoring",
                via_device=(DOMAIN, "hch5_mk1_hac1"),
            )
        else:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, "hch5_mk1_hac1")},
                name="Dantherm HCH PassiveLink",
                manufacturer="Dantherm",
                model="HCH5 MK1 + HAC1",
            )

    @property
    def available(self) -> bool:
        return self.coordinator.available and self.key in self.coordinator.data and self.coordinator.data.get(self.key) is not None
