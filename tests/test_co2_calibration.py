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
