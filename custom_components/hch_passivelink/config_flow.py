"""Config flow for HCH PassiveLink."""

from __future__ import annotations

import asyncio
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import PassiveLinkClient, PassiveSerialClient
from .controller_api import ControllerApiClient
from .const import (
    CONF_CONNECTION_TYPE,
    CONF_SERIAL_PORT,
    CONNECTION_SERIAL,
    CONNECTION_TCP,
    CONF_FILTER_NOTIFY_DAYS,
    CONF_FILTER_NOTIFY_ENABLED,
    CONF_FILTER_NOTIFY_SERVICE,
    CONF_PREHEATER_SENSORS_ENABLED,
    CONF_PREHEATER_SENSOR_HOST,
    CONF_PREHEATER_SENSOR_PORT,
    CONF_PREHEATER_SWAP_SENSORS,
    CONF_CONTROLLER_API_ENABLED,
    CONF_CONTROLLER_HOST,
    CONF_CONTROLLER_PORT,
    CONF_CONTROLLER_TOKEN,
    CONF_SMART_ROOMS_ENABLED,
    CONF_SMART_INPUT_VALID_FOR,
    CONF_SMART_ROOMS,
    DEFAULT_CONTROLLER_PORT,
    DEFAULT_FILTER_NOTIFY_DAYS,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_PREHEATER_SENSOR_PORT,
    DEFAULT_SMART_INPUT_VALID_FOR,
    MAX_SMART_ROOMS,
    SMART_ROOM_PRIORITIES,
    ROOM_SLOT_COUNT,
    room_name_key,
    room_temperature_key,
    room_humidity_key,
    room_co2_key,
    DOMAIN,
)


class PassiveLinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            if user_input[CONF_CONNECTION_TYPE] == CONNECTION_SERIAL:
                return await self.async_step_serial()
            return await self.async_step_tcp()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CONNECTION_TYPE, default=CONNECTION_TCP): vol.In(
                    {CONNECTION_TCP: "RS485 over TCP", CONNECTION_SERIAL: "USB-RS485"}
                )
            }),
        )

    async def async_step_tcp(self, user_input: dict | None = None) -> FlowResult:
        errors = {}
        if user_input is not None:
            host, port = user_input[CONF_HOST], user_input[CONF_PORT]
            try:
                await PassiveLinkClient(host, port, lambda _: None).probe()
            except (OSError, ConnectionError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data={CONF_CONNECTION_TYPE: CONNECTION_TCP, **user_input},
                )
        return self.async_show_form(
            step_id="tcp",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
            }),
            errors=errors,
        )

    async def async_step_serial(self, user_input: dict | None = None) -> FlowResult:
        errors = {}
        if user_input is not None:
            port = user_input[CONF_SERIAL_PORT]
            try:
                await PassiveSerialClient(port, lambda _: None).probe()
            except (OSError, ConnectionError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"serial:{port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data={CONF_CONNECTION_TYPE: CONNECTION_SERIAL, **user_input},
                )
        return self.async_show_form(
            step_id="serial",
            data_schema=vol.Schema({vol.Required(CONF_SERIAL_PORT): str}),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return PassiveLinkOptionsFlow(config_entry)


class PassiveLinkOptionsFlow(config_entries.OptionsFlow):
    """Configure transport, Pi controller API and dynamic HA room sources."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry
        self._pending: dict = {}
        self._rooms = self._load_rooms({**config_entry.data, **config_entry.options})
        self._selected_room: int | None = None

    @property
    def _current(self) -> dict:
        return {**self._config_entry.data, **self._config_entry.options}

    @staticmethod
    def _load_rooms(config: dict) -> list[dict[str, object]]:
        """Load new dynamic rooms, falling back to legacy fixed slots."""
        rooms: list[dict[str, object]] = []
        raw_rooms = config.get(CONF_SMART_ROOMS)
        if isinstance(raw_rooms, list):
            for raw in raw_rooms[:MAX_SMART_ROOMS]:
                if not isinstance(raw, dict):
                    continue
                name = str(raw.get("name", "")).strip()
                if not name:
                    continue
                priority = str(raw.get("priority", "auto"))
                if priority not in SMART_ROOM_PRIORITIES:
                    priority = "auto"
                room = {
                    "name": name[:64],
                    "enabled": bool(raw.get("enabled", True)),
                    "control": bool(raw.get("control", True)),
                    "priority": priority,
                }
                for key in ("temperature", "humidity", "co2"):
                    value = str(raw.get(key, "")).strip()
                    if value:
                        room[key] = value
                rooms.append(room)
            return rooms

        # Transparent migration from the original 8 fixed room slots.
        for slot in range(1, ROOM_SLOT_COUNT + 1):
            name = str(config.get(room_name_key(slot), "")).strip()
            if not name:
                continue
            room: dict[str, object] = {
                "name": name[:64],
                "enabled": True,
                "control": True,
                "priority": "auto",
            }
            for kind, key_func in (
                ("temperature", room_temperature_key),
                ("humidity", room_humidity_key),
                ("co2", room_co2_key),
            ):
                value = str(config.get(key_func(slot), "")).strip()
                if value:
                    room[kind] = value
            if len(room) > 4:
                rooms.append(room)
        return rooms

    @staticmethod
    def _entity_selector():
        return selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", multiple=False)
        )

    def _room_schema(self, room: dict[str, object] | None = None) -> vol.Schema:
        room = room or {}
        entity_selector = self._entity_selector()
        items: dict = {
            vol.Required("name", default=str(room.get("name", ""))): str,
            vol.Required("enabled", default=bool(room.get("enabled", True))): bool,
            vol.Required("control", default=bool(room.get("control", True))): bool,
            vol.Required("priority", default=str(room.get("priority", "auto"))): vol.In({
                "auto": "Auto",
                "low": "Lav",
                "normal": "Normal",
                "high": "Høj",
                "critical": "Kritisk",
            }),
        }
        for key in ("temperature", "humidity", "co2"):
            existing = room.get(key)
            marker = vol.Optional(key, default=existing) if existing else vol.Optional(key)
            items[marker] = entity_selector
        return vol.Schema(items)

    def _validate_room(self, user_input: dict, *, exclude_index: int | None = None) -> tuple[dict, dict]:
        errors: dict = {}
        name = str(user_input.get("name", "")).strip()
        if not name:
            errors["name"] = "required"
        elif any(
            index != exclude_index and str(room.get("name", "")).casefold() == name.casefold()
            for index, room in enumerate(self._rooms)
        ):
            errors["name"] = "room_name_duplicate"

        sensors = {
            key: str(user_input.get(key, "") or "").strip()
            for key in ("temperature", "humidity", "co2")
        }
        if not any(sensors.values()):
            errors["base"] = "room_requires_sensor"

        priority = str(user_input.get("priority", "auto"))
        if priority not in SMART_ROOM_PRIORITIES:
            errors["priority"] = "invalid_priority"

        room: dict[str, object] = {
            "name": name[:64],
            "enabled": bool(user_input.get("enabled", True)),
            "control": bool(user_input.get("control", True)),
            "priority": priority,
        }
        room.update({key: value for key, value in sensors.items() if value})
        return room, errors

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        current = self._current
        errors = {}
        if user_input is not None:
            connection_type = user_input[CONF_CONNECTION_TYPE]
            options = dict(user_input)
            if connection_type == CONNECTION_SERIAL:
                serial_port = str(user_input.get(CONF_SERIAL_PORT, "")).strip()
                if not serial_port:
                    errors[CONF_SERIAL_PORT] = "required"
                else:
                    try:
                        await PassiveSerialClient(serial_port, lambda _: None).probe()
                    except (OSError, ConnectionError, asyncio.TimeoutError):
                        errors["base"] = "cannot_connect"
                    options[CONF_SERIAL_PORT] = serial_port
            else:
                host = str(user_input.get(CONF_HOST, "")).strip()
                port = int(user_input[CONF_PORT])
                if not host:
                    errors[CONF_HOST] = "required"
                else:
                    try:
                        await PassiveLinkClient(host, port, lambda _: None).probe()
                    except (OSError, ConnectionError, asyncio.TimeoutError):
                        errors["base"] = "cannot_connect"
                    options[CONF_HOST] = host
                    options[CONF_PORT] = port
            if not errors:
                self._pending = options
                if user_input.get(CONF_CONTROLLER_API_ENABLED, False):
                    return await self.async_step_controller()
                self._pending[CONF_SMART_ROOMS] = self._rooms
                return self.async_create_entry(title="", data=self._pending)

        schema = vol.Schema({
            vol.Required(
                CONF_CONNECTION_TYPE,
                default=current.get(CONF_CONNECTION_TYPE, CONNECTION_TCP),
            ): vol.In({CONNECTION_TCP: "RS485 over TCP", CONNECTION_SERIAL: "USB-RS485"}),
            vol.Optional(CONF_HOST, default=current.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=current.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Optional(CONF_SERIAL_PORT, default=current.get(CONF_SERIAL_PORT, "")): str,
            vol.Required(
                CONF_FILTER_NOTIFY_ENABLED,
                default=current.get(CONF_FILTER_NOTIFY_ENABLED, True),
            ): bool,
            vol.Required(
                CONF_FILTER_NOTIFY_DAYS,
                default=current.get(CONF_FILTER_NOTIFY_DAYS, DEFAULT_FILTER_NOTIFY_DAYS),
            ): selector.NumberSelector(selector.NumberSelectorConfig(
                min=1, max=180, step=1, mode=selector.NumberSelectorMode.BOX
            )),
            vol.Optional(
                CONF_FILTER_NOTIFY_SERVICE,
                default=current.get(CONF_FILTER_NOTIFY_SERVICE, ""),
            ): str,
            vol.Required(
                CONF_PREHEATER_SENSORS_ENABLED,
                default=current.get(CONF_PREHEATER_SENSORS_ENABLED, False),
            ): bool,
            vol.Optional(
                CONF_PREHEATER_SENSOR_HOST,
                default=current.get(CONF_PREHEATER_SENSOR_HOST, current.get(CONF_HOST, "")),
            ): str,
            vol.Required(
                CONF_PREHEATER_SENSOR_PORT,
                default=current.get(CONF_PREHEATER_SENSOR_PORT, DEFAULT_PREHEATER_SENSOR_PORT),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Required(
                CONF_PREHEATER_SWAP_SENSORS,
                default=current.get(CONF_PREHEATER_SWAP_SENSORS, False),
            ): bool,
            vol.Required(
                CONF_CONTROLLER_API_ENABLED,
                default=current.get(CONF_CONTROLLER_API_ENABLED, True),
            ): bool,
        })
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    async def async_step_controller(self, user_input: dict | None = None) -> FlowResult:
        current = self._current
        errors = {}
        default_host = current.get(CONF_CONTROLLER_HOST) or self._pending.get(CONF_HOST) or current.get(CONF_HOST, "")
        if user_input is not None:
            host = str(user_input[CONF_CONTROLLER_HOST]).strip()
            token = str(user_input[CONF_CONTROLLER_TOKEN]).strip()
            port = int(user_input[CONF_CONTROLLER_PORT])
            if not host:
                errors[CONF_CONTROLLER_HOST] = "required"
            if not token:
                errors[CONF_CONTROLLER_TOKEN] = "required"
            if not errors:
                client = ControllerApiClient(
                    async_get_clientsession(self.hass), host, port, token, lambda _: None
                )
                try:
                    await client.async_probe()
                except (OSError, ConnectionError, asyncio.TimeoutError):
                    errors["base"] = "controller_cannot_connect"
            if not errors:
                self._pending.update(user_input)
                if user_input.get(CONF_SMART_ROOMS_ENABLED, False):
                    return await self.async_step_rooms_menu()
                self._pending[CONF_SMART_ROOMS] = self._rooms
                return self.async_create_entry(title="", data=self._pending)

        schema = vol.Schema({
            vol.Required(CONF_CONTROLLER_HOST, default=default_host): str,
            vol.Required(
                CONF_CONTROLLER_PORT,
                default=current.get(CONF_CONTROLLER_PORT, DEFAULT_CONTROLLER_PORT),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Required(
                CONF_CONTROLLER_TOKEN,
                default=current.get(CONF_CONTROLLER_TOKEN, ""),
            ): selector.TextSelector(selector.TextSelectorConfig(
                type=selector.TextSelectorType.PASSWORD
            )),
            vol.Required(
                CONF_SMART_ROOMS_ENABLED,
                default=current.get(CONF_SMART_ROOMS_ENABLED, True),
            ): bool,
            vol.Required(
                CONF_SMART_INPUT_VALID_FOR,
                default=current.get(CONF_SMART_INPUT_VALID_FOR, DEFAULT_SMART_INPUT_VALID_FOR),
            ): selector.NumberSelector(selector.NumberSelectorConfig(
                min=30, max=900, step=30, mode=selector.NumberSelectorMode.BOX
            )),
        })
        return self.async_show_form(step_id="controller", data_schema=schema, errors=errors)

    async def async_step_rooms_menu(self, user_input: dict | None = None) -> FlowResult:
        del user_input
        options = []
        if len(self._rooms) < MAX_SMART_ROOMS:
            options.append("add_room")
        if self._rooms:
            options.extend(("edit_room", "remove_room"))
        options.append("finish_rooms")
        return self.async_show_menu(step_id="rooms_menu", menu_options=options)

    async def async_step_add_room(self, user_input: dict | None = None) -> FlowResult:
        errors = {}
        if user_input is not None:
            room, errors = self._validate_room(user_input)
            if not errors:
                self._rooms.append(room)
                return await self.async_step_rooms_menu()
        return self.async_show_form(
            step_id="add_room",
            data_schema=self._room_schema(),
            errors=errors,
        )

    async def async_step_edit_room(self, user_input: dict | None = None) -> FlowResult:
        if not self._rooms:
            return await self.async_step_rooms_menu()
        choices = {str(index): str(room["name"]) for index, room in enumerate(self._rooms)}
        if user_input is not None:
            self._selected_room = int(user_input["room"])
            return await self.async_step_room_detail()
        return self.async_show_form(
            step_id="edit_room",
            data_schema=vol.Schema({vol.Required("room"): vol.In(choices)}),
        )

    async def async_step_room_detail(self, user_input: dict | None = None) -> FlowResult:
        if self._selected_room is None or self._selected_room >= len(self._rooms):
            return await self.async_step_rooms_menu()
        current = self._rooms[self._selected_room]
        errors = {}
        if user_input is not None:
            room, errors = self._validate_room(user_input, exclude_index=self._selected_room)
            if not errors:
                self._rooms[self._selected_room] = room
                self._selected_room = None
                return await self.async_step_rooms_menu()
        return self.async_show_form(
            step_id="room_detail",
            data_schema=self._room_schema(current),
            errors=errors,
        )

    async def async_step_remove_room(self, user_input: dict | None = None) -> FlowResult:
        if not self._rooms:
            return await self.async_step_rooms_menu()
        choices = {str(index): str(room["name"]) for index, room in enumerate(self._rooms)}
        if user_input is not None:
            index = int(user_input["room"])
            if 0 <= index < len(self._rooms):
                self._rooms.pop(index)
            return await self.async_step_rooms_menu()
        return self.async_show_form(
            step_id="remove_room",
            data_schema=vol.Schema({vol.Required("room"): vol.In(choices)}),
        )

    async def async_step_finish_rooms(self, user_input: dict | None = None) -> FlowResult:
        del user_input
        self._pending[CONF_SMART_ROOMS] = self._rooms
        # Do not persist the old fixed-slot representation when options are saved.
        for slot in range(1, ROOM_SLOT_COUNT + 1):
            for key_func in (room_name_key, room_temperature_key, room_humidity_key, room_co2_key):
                self._pending.pop(key_func(slot), None)
        return self.async_create_entry(title="", data=self._pending)
