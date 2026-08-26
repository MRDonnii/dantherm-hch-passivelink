"""Coordinator for HCH PassiveLink."""

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .filter import filter_values

STORE_VERSION = 1

class PassiveLinkCoordinator(DataUpdateCoordinator[dict[str, object]]):
    def __init__(self, hass: HomeAssistant, client, entry_id: str) -> None:
        super().__init__(hass, logger=__import__("logging").getLogger(__name__), name="Dantherm HCH PassiveLink")
        self.data = {}
        self.client = client
        self.task = None
        self._filter_store = Store(
            hass, STORE_VERSION, f"hch_passivelink.{entry_id}.filter_state"
        )
        self._filter_reset_epoch: float | None = None
        self._filter_interval_days: int | None = None
        self._remove_filter_timer = None

    async def async_load_filter_state(self) -> None:
        """Load filter state before entities are created."""
        stored = await self._filter_store.async_load()
        if isinstance(stored, dict):
            reset = stored.get("reset_epoch")
            interval = stored.get("interval_days")
            if isinstance(reset, (int, float)) and isinstance(interval, int) and interval > 0:
                self._filter_reset_epoch = float(reset)
                self._filter_interval_days = interval
                self.data.update(filter_values(float(reset), interval))
        self._remove_filter_timer = async_track_time_interval(
            self.hass, self._async_update_filter_clock, timedelta(hours=1)
        )

    def async_handle_update(self, data: dict[str, object]) -> None:
        """Merge decoded traffic with persistent filter data."""
        interval = data.get("filter_interval_days")
        if isinstance(interval, int) and interval > 0:
            changed = interval != self._filter_interval_days
            self._filter_interval_days = interval
            if changed and self._filter_reset_epoch is not None:
                self.hass.async_create_task(
                    self._filter_store.async_save(
                        {
                            "reset_epoch": self._filter_reset_epoch,
                            "interval_days": interval,
                        }
                    )
                )
        merged = dict(data)
        if self._filter_reset_epoch is not None and self._filter_interval_days is not None:
            merged.update(filter_values(self._filter_reset_epoch, self._filter_interval_days))
        self.async_set_updated_data(merged)

    async def _async_update_filter_clock(self, _now) -> None:
        if self._filter_reset_epoch is None or self._filter_interval_days is None:
            return
        merged = dict(self.data)
        merged.update(filter_values(self._filter_reset_epoch, self._filter_interval_days))
        self.async_set_updated_data(merged)

    async def async_shutdown(self) -> None:
        if self._remove_filter_timer is not None:
            self._remove_filter_timer()
            self._remove_filter_timer = None

    @property
    def available(self) -> bool:
        return self.client.connected and bool(self.data)
