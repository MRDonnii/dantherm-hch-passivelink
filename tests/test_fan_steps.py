import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components"))

pytest.importorskip("homeassistant")
pytest.importorskip("serial")
from hch_passivelink.fan import HCHControllerFan  # noqa: E402
from hch_passivelink.number import SPECS, ControllerNumber, FanProfileNumber, FanSettingNumber, FAN_SETTINGS  # noqa: E402
from hch_passivelink.select import ControllerLevelSelect, StepControlSelect  # noqa: E402

FOUR = {
    "mode": "manual", "manual_level": 4, "effective_level": 4, "fan_step_count": 4, "max_level": 4,
    "local_normal_level": 3,
    "fan_settings": {"supply": 55, "extract": 70, "offset": 25, "max_supply": 100, "max_extract": 100},
    "profiles": {"1": {"extract": 20, "supply": 13}, "2": {"extract": 45, "supply": 34},
                 "3": {"extract": 70, "supply": 55}, "4": {"extract": 100, "supply": 80}},
}


class Coordinator:
    def __init__(self, state):
        self.controller_state = dict(state)
        self.controller_client = SimpleNamespace(connected=True)
        self.sent = []

    async def async_controller_command(self, patch):
        self.sent.append(patch)


def test_four_dantherm_steps_limit_every_level_entity():
    coordinator = Coordinator(FOUR)
    level = ControllerLevelSelect(coordinator)
    assert level.options == ["OFF", "1", "2", "3", "4"]
    fan = HCHControllerFan(coordinator)
    assert fan.preset_modes == ["Auto", "Smart Auto", "Niveau 1", "Niveau 2", "Niveau 3", "Boost"]
    assert fan.preset_mode == "Boost"
    asyncio.run(fan.async_set_preset_mode("Boost"))
    assert coordinator.sent[-1] == {"mode": "manual", "manual_level": 4}
    normal = ControllerNumber(coordinator, next(spec for spec in SPECS if spec.key == "local_normal_level"))
    assert normal.native_max_value == 4
    assert not FanProfileNumber(coordinator, 5, "extract").available
    assert FanProfileNumber(coordinator, 3, "supply").native_value == 55


def test_commissioning_and_step_choice_are_sent_to_the_pi():
    coordinator = Coordinator(FOUR)
    numbers = {spec[0]: FanSettingNumber(coordinator, *spec) for spec in FAN_SETTINGS}
    assert numbers["offset"].available and numbers["offset"].native_value == 25
    asyncio.run(numbers["extract"].async_set_native_value(72))
    assert coordinator.sent[-1] == {"fan_settings": {"extract": 72}}
    steps = StepControlSelect(coordinator)
    assert steps.current_option == "4 trin (Dantherm)"
    asyncio.run(steps.async_select_option("6 trin"))
    assert coordinator.sent[-1] == {"fan_step_count": 6}


def test_six_steps_and_older_controllers_keep_six_levels():
    coordinator = Coordinator({"manual_level": 6, "mode": "manual", "profiles": {str(n): {} for n in range(1, 7)}})
    assert ControllerLevelSelect(coordinator).options[-1] == "6"
    assert HCHControllerFan(coordinator).preset_mode == "Boost"
    assert not FanSettingNumber(coordinator, *FAN_SETTINGS[0]).available
    assert not StepControlSelect(coordinator).available


def test_vacation_switch_starts_now_without_end_and_level_follows_steps():
    from hch_passivelink.switch import VacationSwitch
    coordinator = Coordinator({**FOUR, "vacation_enabled": False, "vacation_level": 1})
    switch = VacationSwitch(coordinator)
    assert switch.available and not switch.is_on
    asyncio.run(switch.async_turn_on())
    assert coordinator.sent[-1] == {"vacation_enabled": True, "vacation_from": None, "vacation_until": None}
    asyncio.run(switch.async_turn_off())
    assert coordinator.sent[-1] == {"vacation_enabled": False}
    level = ControllerNumber(coordinator, next(spec for spec in SPECS if spec.key == "vacation_level"))
    assert level.native_value == 1 and level.native_max_value == 4
