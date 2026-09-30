import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components"))

pytest.importorskip("homeassistant")
pytest.importorskip("serial")
from hch_passivelink.coordinator import PassiveLinkCoordinator  # noqa: E402
from hch_passivelink.smart_coordinator import SmartPassiveLinkCoordinator  # noqa: E402


def _apply(controller_state, co2):
    fake = SimpleNamespace(controller_state=controller_state)
    fake.co2_offset = lambda: SmartPassiveLinkCoordinator.co2_offset(fake)
    data = {"co2": co2}
    PassiveLinkCoordinator._apply_co2_calibration(fake, data)
    PassiveLinkCoordinator._update_air_quality(fake, data)
    return data


def test_pi_calibration_is_applied_to_unit_co2():
    data = _apply({"co2_offset": -200}, 815)
    assert data["co2"] == 615 and data["air_quality_index"] == "good"


def test_no_controller_or_offset_leaves_co2_unchanged():
    assert _apply({}, 815)["co2"] == 815
    assert _apply({"co2_offset": "x"}, 815)["co2"] == 815


def test_calibrated_co2_never_goes_negative():
    assert _apply({"co2_offset": -1000}, 400)["co2"] == 0


def test_bonfire_select_maps_options_to_minutes():
    from hch_passivelink.select import BONFIRE_OPTIONS, BonfireDurationSelect
    assert BONFIRE_OPTIONS["2 timer"] == 120 and BONFIRE_OPTIONS["Slukket"] == 0
    fake = SimpleNamespace(coordinator=SimpleNamespace(controller_state={"bonfire_active": True, "bonfire_minutes": 60}))
    assert BonfireDurationSelect.current_option.fget(fake) == "1 time"
    fake.coordinator.controller_state = {"bonfire_active": False, "bonfire_minutes": 0}
    assert BonfireDurationSelect.current_option.fget(fake) == "Slukket"


def test_level_select_offers_off_and_shows_it_in_standby():
    from hch_passivelink.select import ControllerLevelSelect
    options = ControllerLevelSelect.options.fget(SimpleNamespace(max_level=4))
    assert options == ["OFF", "1", "2", "3", "4"]
    fake = SimpleNamespace(coordinator=SimpleNamespace(controller_state={"standby_active": True, "manual_level": 3}))
    assert ControllerLevelSelect.current_option.fget(fake) == "OFF"
    fake.coordinator.controller_state = {"standby_active": False, "manual_level": 3}
    assert ControllerLevelSelect.current_option.fget(fake) == "3"


def test_standby_select_maps_options_to_minutes():
    from hch_passivelink.select import STANDBY_OPTIONS, StandbyDurationSelect
    assert STANDBY_OPTIONS["Permanent"] == -1 and STANDBY_OPTIONS["Til i morgen kl. 07"] == -2
    fake = SimpleNamespace(coordinator=SimpleNamespace(controller_state={"standby_active": True, "standby_minutes": -2}))
    assert StandbyDurationSelect.current_option.fget(fake) == "Til i morgen kl. 07"
    fake.coordinator.controller_state = {"standby_active": False, "standby_minutes": 0}
    assert StandbyDurationSelect.current_option.fget(fake) == "Tændt"
