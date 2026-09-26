import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components"))

pytest.importorskip("homeassistant")
pytest.importorskip("serial")
from hch_passivelink.smart_coordinator import SmartPassiveLinkCoordinator  # noqa: E402


def _signal(field, state, unit):
    states = {"sensor.x": SimpleNamespace(state=state, attributes={"unit_of_measurement": unit})}
    fake = SimpleNamespace(hass=SimpleNamespace(states=SimpleNamespace(get=states.get)))
    return SmartPassiveLinkCoordinator._energy_signal(fake, field, "sensor.x")


def test_energy_is_sent_in_kwh():
    assert _signal("unit_energy_measured_today_kwh", "1.36", "kWh") == pytest.approx(1.36)
    assert _signal("unit_energy_measured_today_kwh", "1360", "Wh") == pytest.approx(1.36)
    assert _signal("unit_energy_measured_today_kwh", "unavailable", "kWh") is None


def test_prices_are_sent_in_kr_per_kwh():
    assert _signal("electricity_price_dkk_kwh", "2.1", "DKK/kWh") == pytest.approx(2.1)
    assert _signal("electricity_price_dkk_kwh", "210", "øre/kWh") == pytest.approx(2.1)
    assert _signal("heat_price_dkk_kwh", "600", "DKK/MWh") == pytest.approx(0.6)
    assert _signal("heat_price_dkk_kwh", "-1", "kr/kWh") is None
