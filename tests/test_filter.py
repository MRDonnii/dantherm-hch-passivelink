import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "hch_passivelink"))

from filter import filter_values


def test_filter_values_continue_from_original_reset():
    reset = 1_784_144_016.9482355
    values = filter_values(reset, 360, reset + 42.01 * 86400)
    assert values["filter_days_remaining"] == 318
    assert values["filter_life_percent"] == 88
    assert values["filter_status"] == "ok"
    assert values["filter_alarm"] is False
