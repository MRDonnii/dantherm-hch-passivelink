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
    DEFAULT_CONTROLLER_PORT,
    DEFAULT_FILTER_NOTIFY_DAYS,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_PREHEATER_SENSOR_PORT,
    DEFAULT_SMART_INPUT_VALID_FOR,
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
    """Configure transport, Pi controller API and optional HA room sources."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry
        self._pending: dict = {}

    @property
    def _current(self) -> dict:
        return {**self._config_entry.data, **self._config_entry.options}

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
                    return await self.async_step_rooms()
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

    async def async_step_rooms(self, user_input: dict | None = None) -> FlowResult:
        current = self._current
        if user_input is not None:
            cleaned = {}
            for key, value in user_input.items():
                if value is not None:
                    cleaned[key] = str(value).strip() if isinstance(value, str) else value
            self._pending.update(cleaned)
            return self.async_create_entry(title="", data=self._pending)

        schema_items: dict = {}
        entity_selector = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", multiple=False)
        )
        for slot in range(1, ROOM_SLOT_COUNT + 1):
            name_key = room_name_key(slot)
            temp_key = room_temperature_key(slot)
            rh_key = room_humidity_key(slot)
            co2_key = room_co2_key(slot)
            schema_items[vol.Optional(name_key, default=current.get(name_key, ""))] = str
            for key in (temp_key, rh_key, co2_key):
                existing = current.get(key)
                marker = vol.Optional(key, default=existing) if existing else vol.Optional(key)
                schema_items[marker] = entity_selector
        return self.async_show_form(
            step_id="rooms",
            data_schema=vol.Schema(schema_items),
        )
