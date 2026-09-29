import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components"))

import pytest  # noqa: E402

pytest.importorskip("homeassistant")
pytest.importorskip("serial")
from hch_passivelink.smart_coordinator import SmartPassiveLinkCoordinator  # noqa: E402


def _payload(sources, values):
    states = {
        entity_id: SimpleNamespace(state=value, attributes={})
        for entity_id, value in values.items()
    }
    fake = SimpleNamespace(
        room_sources=sources,
        hass=SimpleNamespace(states=SimpleNamespace(get=states.get)),
    )
    return SmartPassiveLinkCoordinator._room_payload(fake)


def test_room_payload_matches_pi_contract():
    rooms = _payload(
        [
            {"name": "Køkken", "co2": "sensor.co2", "pm25": "sensor.pm25",
             "humidity": "sensor.rh", "priority": "high", "room_type": "normal"},
            {"name": "Bad", "humidity": "sensor.bath", "room_type": "bathroom"},
        ],
        {"sensor.co2": "668", "sensor.pm25": "42", "sensor.rh": "unavailable",
         "sensor.bath": "71"},
    )
    assert rooms["Køkken"]["co2"] == 668
    assert rooms["Køkken"]["pm25"] == 42
    assert "humidity" not in rooms["Køkken"]
    assert rooms["Køkken"]["room_type"] == "normal"
    assert rooms["Køkken"]["entities"] == {"co2": "sensor.co2", "pm25": "sensor.pm25"}
    assert rooms["Bad"]["room_type"] == "bathroom"


def test_out_of_range_values_are_skipped_not_sent():
    # One bad value would make the Pi reject the whole message with HTTP 400.
    rooms = _payload(
        [{"name": "Stue", "co2": "sensor.co2", "pm25": "sensor.pm25"}],
        {"sensor.co2": "5", "sensor.pm25": "nan"},
    )
    assert rooms == {}
