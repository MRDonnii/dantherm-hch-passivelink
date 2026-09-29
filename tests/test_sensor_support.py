import importlib.util
from pathlib import Path
from types import SimpleNamespace

# Load the module directly so the test needs no Home Assistant install.
_PATH = Path(__file__).parents[1] / "custom_components" / "hch_passivelink" / "sensor_support.py"
_SPEC = importlib.util.spec_from_file_location("sensor_support", _PATH)
sensor_support = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sensor_support)


def _state(entity_id, device_class=None, unit=None):
    attributes = {}
    if device_class:
        attributes["device_class"] = device_class
    if unit:
        attributes["unit_of_measurement"] = unit
    return SimpleNamespace(entity_id=entity_id, attributes=attributes)


STATES = [
    _state("sensor.living_temperature", "temperature", "°C"),
    _state("sensor.attic_temperature_f", "temperature", "°F"),
    _state("sensor.bath_humidity", "humidity", "%"),
    _state("sensor.phone_battery", "battery", "%"),
    _state("sensor.office_co2", "carbon_dioxide", "ppm"),
    _state("sensor.tvoc", "volatile_organic_compounds_parts", "ppm"),
    _state("sensor.kitchen_pm25", "pm25", "µg/m³"),
    _state("sensor.kitchen_pm10", "pm10", "µg/m³"),
    _state("sensor.shelly_power", "power", "W"),
    _state("sensor.unit_energy_today", "energy", "kWh"),
    _state("sensor.nordpool", None, "øre/kWh"),
    _state("sensor.district_heat_price", "monetary", "DKK/MWh"),
    _state("sensor.eur_price", "monetary", "EUR/kWh"),
    _state("binary_sensor.window", None, None),
]


def test_room_sensors_only_list_matching_types():
    ids = lambda kind: sensor_support.supported_entity_ids(STATES, kind)
    assert ids("temperature") == ["sensor.living_temperature"]
    assert ids("humidity") == ["sensor.bath_humidity"]
    assert ids("co2") == ["sensor.office_co2"]
    assert ids("pm25") == ["sensor.kitchen_pm25"]


def test_energy_sensors_only_list_supported_units():
    ids = lambda kind: sensor_support.supported_entity_ids(STATES, kind)
    assert ids("power") == ["sensor.shelly_power"]
    assert ids("energy") == ["sensor.unit_energy_today"]
    assert ids("price") == ["sensor.district_heat_price", "sensor.nordpool"]


def test_existing_selection_stays_visible():
    ids = sensor_support.supported_entity_ids(STATES, "humidity", keep="sensor.gone")
    assert ids == ["sensor.bath_humidity", "sensor.gone"]
