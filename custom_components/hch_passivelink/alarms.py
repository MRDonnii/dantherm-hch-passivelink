"""Conservative alarms derived from verified PassiveLink measurements."""

from collections.abc import Mapping

FAN_ALARM_MIN_COMMAND_PERCENT = 20
FAN_ALARM_MAX_RPM = 100
OUTDOOR_TEMPERATURE_ALARM_C = -13
SUPPLY_TEMPERATURE_ALARM_C = 5
FIRE_TEMPERATURE_ALARM_C = 70

TEMPERATURE_SENSOR_ALARMS = {
    "outdoor_temperature_sensor_fault": "outdoor_temperature",
    "supply_temperature_sensor_fault": "supply_temperature",
    "extract_temperature_sensor_fault": "extract_temperature",
    "exhaust_temperature_sensor_fault": "exhaust_temperature",
    "room_temperature_sensor_fault": "room_temperature",
}


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float))


def derive_alarm_values(data: Mapping[str, object]) -> dict[str, bool]:
    """Return alarms the observed bus values can establish safely."""
    extract_percent = data.get("extract_fan_percent")
    supply_percent = data.get("supply_fan_percent")
    extract_rpm = data.get("extract_fan_rpm")
    supply_rpm = data.get("supply_fan_rpm")
    alarms = {
        "extract_fan_fault": _is_number(extract_percent) and extract_percent >= FAN_ALARM_MIN_COMMAND_PERCENT and _is_number(extract_rpm) and extract_rpm < FAN_ALARM_MAX_RPM,
        "supply_fan_fault": _is_number(supply_percent) and supply_percent >= FAN_ALARM_MIN_COMMAND_PERCENT and _is_number(supply_rpm) and supply_rpm < FAN_ALARM_MAX_RPM,
    }
    complete_snapshot = data.get("temperature_source") == "hac1_snapshot_180_209" and data.get("temperature_sample_monotonic") is not None
    alarms.update({key: complete_snapshot and data.get(sensor) is None for key, sensor in TEMPERATURE_SENSOR_ALARMS.items()})
    outdoor, supply, extract = data.get("outdoor_temperature"), data.get("supply_temperature"), data.get("extract_temperature")
    alarms.update(
        outdoor_temperature_low=_is_number(outdoor) and outdoor < OUTDOOR_TEMPERATURE_ALARM_C,
        supply_temperature_low=_is_number(supply) and supply < SUPPLY_TEMPERATURE_ALARM_C,
        fire_temperature_alarm=_is_number(extract) and extract > FIRE_TEMPERATURE_ALARM_C,
    )
    return alarms
