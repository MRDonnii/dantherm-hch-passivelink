import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "hch_passivelink"))

from alarms import derive_alarm_values


def test_fan_alarm_requires_command_and_stopped_fan():
    assert derive_alarm_values({"supply_fan_percent": 74, "supply_fan_rpm": 0})["supply_fan_fault"] is True
    assert derive_alarm_values({"supply_fan_percent": 0, "supply_fan_rpm": 0})["supply_fan_fault"] is False


def test_sensor_fault_requires_complete_snapshot():
    data = {"temperature_source": "hac1_snapshot_180_209", "temperature_sample_monotonic": 1.0, "room_temperature": None}
    assert derive_alarm_values(data)["room_temperature_sensor_fault"] is True
    assert derive_alarm_values({"room_temperature": None})["room_temperature_sensor_fault"] is False


def test_temperature_thresholds_are_strict():
    assert derive_alarm_values({"outdoor_temperature": -13})["outdoor_temperature_low"] is False
    assert derive_alarm_values({"outdoor_temperature": -13.01})["outdoor_temperature_low"] is True
    assert derive_alarm_values({"supply_temperature": 4.99})["supply_temperature_low"] is True
    assert derive_alarm_values({"extract_temperature": 70.01})["fire_temperature_alarm"] is True
