"""PassiveLink coordinator extensions for Pi control and HA room inputs."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import Event, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

from .coordinator import PassiveLinkCoordinator

_LOGGER = logging.getLogger(__name__)


class SmartPassiveLinkCoordinator(PassiveLinkCoordinator):
    """Keep PassiveLink receive-only while adding a separate Pi controller API."""

    def __init__(self, *args, controller_client=None, room_sources=None,
                 smart_input_valid_for: int = 180, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.controller_client = controller_client
        self.controller_state: dict[str, object] = {}
        self.controller_task = None
        self.room_sources = list(room_sources or [])
        self.smart_input_valid_for = max(30, min(900, int(smart_input_valid_for)))
        self._remove_room_listener = None
        self._remove_room_timer = None
        self._room_send_task: asyncio.Task | None = None

    @callback
    def async_handle_controller_update(self, state: dict[str, object]) -> None:
        self.controller_state = dict(state)
        # Controller entities use the same coordinator listener mechanism as
        # PassiveLink entities, but controller state remains separately namespaced.
        self.async_update_listeners()

    async def async_controller_command(self, patch: dict[str, object]) -> dict[str, object]:
        if self.controller_client is None:
            raise ConnectionError("Controller API is not configured")
        return await self.controller_client.async_command(patch)

    def _room_payload(self) -> dict[str, dict[str, float]]:
        rooms: dict[str, dict[str, float]] = {}
        for source in self.room_sources:
            name = str(source.get("name") or "").strip()
            if not name:
                continue
            values: dict[str, float] = {}
            for kind in ("temperature", "humidity", "co2"):
                entity_id = source.get(kind)
                if not entity_id:
                    continue
                state = self.hass.states.get(entity_id)
                if state is None or state.state in {"unknown", "unavailable", "none", ""}:
                    continue
                try:
                    value = float(state.state)
                except (TypeError, ValueError):
                    continue
                if kind == "humidity" and not 0 <= value <= 100:
                    continue
                if kind == "co2" and not 250 <= value <= 10000:
                    continue
                if kind == "temperature" and not -30 <= value <= 60:
                    continue
                values[kind] = value
            if values:
                rooms[name] = values
        return rooms

    async def async_send_room_inputs(self) -> None:
        if self.controller_client is None or not self.room_sources:
            return
        try:
            await self.controller_client.async_send_rooms(
                self._room_payload(), self.smart_input_valid_for
            )
        except (OSError, ConnectionError, asyncio.TimeoutError) as error:
            _LOGGER.debug("Unable to push room data to Pi controller: %s", error)

    @callback
    def _schedule_room_push(self, _event: Event | None = None) -> None:
        if self._room_send_task is not None and not self._room_send_task.done():
            return

        async def delayed_push() -> None:
            await asyncio.sleep(1)
            await self.async_send_room_inputs()

        self._room_send_task = self.hass.async_create_task(delayed_push())

    async def async_start_controller(self) -> None:
        if self.controller_client is None:
            return
        self.controller_client._update = self.async_handle_controller_update
        self.controller_task = self.hass.async_create_task(
            self.controller_client.run(), "Dantherm HCH Pi controller API"
        )
        entity_ids = sorted({
            entity_id
            for source in self.room_sources
            for entity_id in (
                source.get("temperature"), source.get("humidity"), source.get("co2")
            )
            if entity_id
        })
        if entity_ids:
            self._remove_room_listener = async_track_state_change_event(
                self.hass, entity_ids, self._schedule_room_push
            )
            self._remove_room_timer = async_track_time_interval(
                self.hass,
                lambda _now: self._schedule_room_push(),
                timedelta(seconds=60),
            )
            self._schedule_room_push()

    async def async_shutdown(self) -> None:
        if self._remove_room_listener is not None:
            self._remove_room_listener()
            self._remove_room_listener = None
        if self._remove_room_timer is not None:
            self._remove_room_timer()
            self._remove_room_timer = None
        if self._room_send_task is not None:
            self._room_send_task.cancel()
            try:
                await self._room_send_task
            except asyncio.CancelledError:
                pass
            self._room_send_task = None
        if self.controller_client is not None:
            await self.controller_client.stop()
        if self.controller_task is not None:
            self.controller_task.cancel()
            try:
                await self.controller_task
            except asyncio.CancelledError:
                pass
            self.controller_task = None
        await super().async_shutdown()
