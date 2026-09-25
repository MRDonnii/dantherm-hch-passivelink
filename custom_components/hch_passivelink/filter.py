"""Persistent filter-life calculations."""

from __future__ import annotations

import math
import time


def filter_values(
    reset_epoch: float, interval_days: int, now: float | None = None
) -> dict[str, object]:
    """Return current filter state without changing the stored reset time."""
    current = time.time() if now is None else now
    elapsed_days = max(0.0, (current - reset_epoch) / 86400.0)
    remaining = max(0, math.ceil(interval_days - elapsed_days))
    percent = max(0, min(100, round(remaining / interval_days * 100)))
    if remaining <= 0:
        status = "overdue"
    elif remaining <= 30:
        status = "change_soon"
    else:
        status = "ok"
    return {
        "filter_interval_days": interval_days,
        "filter_days_remaining": remaining,
        "filter_life_percent": percent,
        "filter_status": status,
        "filter_alarm": remaining <= 0,
        "filter_source": "hcp4_synchronized",
    }
