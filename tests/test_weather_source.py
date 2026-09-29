import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

_PATH = Path(__file__).parents[1] / "custom_components" / "hch_passivelink" / "weather_source.py"
_SPEC = importlib.util.spec_from_file_location("weather_source", _PATH)
weather_source = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(weather_source)


def _state(now, **attributes):
    return SimpleNamespace(state="cloudy", last_updated=now, attributes=attributes)


def test_weather_entity_sends_current_humidity_and_dew_point():
    now = datetime.now(timezone.utc)
    payload = weather_source.weather_payload("weather.forecast_langaa", _state(
        now, temperature=16, humidity=71, dew_point=10, temperature_unit="°C"), now=now)
    assert payload == {"source": "weather.forecast_langaa", "condition": "cloudy",
                       "temperature_c": 16, "dew_point_c": 10, "humidity_pct": 71}


def test_stale_or_unavailable_weather_is_not_renewed():
    now = datetime.now(timezone.utc)
    assert weather_source.weather_payload("weather.home", _state(now - timedelta(hours=3)), now=now) is None
    unavailable = _state(now)
    unavailable.state = "unavailable"
    assert weather_source.weather_payload("weather.home", unavailable, now=now) is None


def test_fahrenheit_is_converted_before_sending():
    now = datetime.now(timezone.utc)
    payload = weather_source.weather_payload("weather.home", _state(
        now, temperature=68, dew_point=50, humidity=50, temperature_unit="°F"), now=now)
    assert payload["temperature_c"] == 20
    assert payload["dew_point_c"] == 10
