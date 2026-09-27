import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components"))

pytest.importorskip("homeassistant")
pytest.importorskip("serial")
from hch_passivelink.number import SPECS, ControllerNumber  # noqa: E402
from hch_passivelink.sensor import BalanceStatusSensor  # noqa: E402
from hch_passivelink.switch import BalanceSwitch  # noqa: E402

STATE = {
    "balance_enabled": True,
    "balance_extract_excess_percent": 5.0,
    "balance_duct_ratio": 1.14,
    "balance_running_excess_percent": 4.8,
    "balance": {
        "enabled": True, "target_excess_percent": 5.0, "duct_ratio": 1.14, "duct_ratio_source": "fixed",
        "levels": {"1": {"supply": 17, "extract": 25}, "2": {"supply": 30, "extract": 40}},
        "learned": {"ratio": 1.15, "ratio_in_use": None, "count": 6, "nights": 1, "confidence": "low",
                    "last": {"reason": "Målt: udsugning +4,8 %"}},
        "error": None,
    },
    "balance_live": {"state": "measuring", "reason": "Måler varmebalancen", "delta_t_now": 10.2, "excess_now_percent": 4.6},
}


class Coordinator:
    def __init__(self):
        self.controller_state = dict(STATE)
        self.controller_client = SimpleNamespace(connected=True)
        self.sent = []

    async def async_controller_command(self, patch):
        self.sent.append(patch)


def test_balance_switch_reads_and_sends():
    coordinator = Coordinator()
    switch = BalanceSwitch(coordinator)
    assert switch.available and switch.is_on
    assert switch.extra_state_attributes["trin"]["1"] == "17/25 %"
    asyncio.run(switch.async_turn_off())
    assert coordinator.sent == [{"balance_enabled": False}]


def test_balance_numbers_keep_fractions():
    coordinator = Coordinator()
    spec = next(spec for spec in SPECS if spec.key == "balance_duct_ratio")
    number = ControllerNumber(coordinator, spec)
    assert number.native_value == 1.14
    asyncio.run(number.async_set_native_value(1.12))
    assert coordinator.sent == [{"balance_duct_ratio": 1.12}]


def test_balance_sensors():
    coordinator = Coordinator()
    ratio = BalanceStatusSensor(coordinator, "balance_duct_ratio_in_use", "x", "mdi:pipe")
    live = BalanceStatusSensor(coordinator, "balance_heat_balance", "y", "mdi:heat-wave")
    assert ratio.native_value == 1.14
    assert ratio.extra_state_attributes["laert_kanalforhold"] == 1.15
    assert live.native_value == "Måler varmebalancen"
    assert live.extra_state_attributes["udsugning_over_indblaesning_nu_pct"] == 4.6
    coordinator.controller_state = {}
    assert not ratio.available
