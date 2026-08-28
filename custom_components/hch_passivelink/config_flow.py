"""Config flow for HCH PassiveLink."""

from __future__ import annotations

import asyncio
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .client import PassiveLinkClient, PassiveSerialClient
from .const import (
    CONF_CONNECTION_TYPE,
    CONF_SERIAL_PORT,
    CONNECTION_SERIAL,
    CONNECTION_TCP,
    CONF_FILTER_NOTIFY_DAYS,
    CONF_FILTER_NOTIFY_ENABLED,
    CONF_FILTER_NOTIFY_SERVICE,
    DEFAULT_FILTER_NOTIFY_DAYS,
    DEFAULT_NAME,
    DEFAULT_PORT,
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
        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        })
        return self.async_show_form(step_id="tcp", data_schema=schema, errors=errors)

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
    """Change transport without replacing the config entry or entities."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry
        self._connection_type = CONNECTION_TCP
        self._notification_options = {}

    @property
    def _current(self) -> dict:
        return {**self._config_entry.data, **self._config_entry.options}

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        current = self._current
        errors = {}
        if user_input is not None:
            self._connection_type = user_input[CONF_CONNECTION_TYPE]
            connection_options = {
                CONF_CONNECTION_TYPE: self._connection_type,
                CONF_FILTER_NOTIFY_ENABLED: user_input[CONF_FILTER_NOTIFY_ENABLED],
                CONF_FILTER_NOTIFY_DAYS: int(user_input[CONF_FILTER_NOTIFY_DAYS]),
                CONF_FILTER_NOTIFY_SERVICE: user_input[CONF_FILTER_NOTIFY_SERVICE].strip(),
            }
            if self._connection_type == CONNECTION_SERIAL:
                serial_port = user_input.get(CONF_SERIAL_PORT, "").strip()
                if not serial_port:
                    errors[CONF_SERIAL_PORT] = "required"
                else:
                    try:
                        await PassiveSerialClient(serial_port, lambda _: None).probe()
                    except (OSError, ConnectionError, asyncio.TimeoutError):
                        errors["base"] = "cannot_connect"
                    else:
                        connection_options[CONF_SERIAL_PORT] = serial_port
            else:
                host = user_input.get(CONF_HOST, "").strip()
                port = user_input[CONF_PORT]
                if not host:
                    errors[CONF_HOST] = "required"
                else:
                    try:
                        await PassiveLinkClient(host, port, lambda _: None).probe()
                    except (OSError, ConnectionError, asyncio.TimeoutError):
                        errors["base"] = "cannot_connect"
                    else:
                        connection_options.update({CONF_HOST: host, CONF_PORT: port})
            if not errors:
                return self.async_create_entry(title="", data=connection_options)
        schema: dict = {
                vol.Required(
                    CONF_CONNECTION_TYPE,
                    default=current.get(CONF_CONNECTION_TYPE, CONNECTION_TCP),
                ): vol.In({
                    CONNECTION_TCP: "RS485 over TCP",
                    CONNECTION_SERIAL: "USB-RS485",
                }),
                vol.Required(
                    CONF_FILTER_NOTIFY_ENABLED,
                    default=current.get(CONF_FILTER_NOTIFY_ENABLED, True),
                ): bool,
                vol.Required(
                    CONF_FILTER_NOTIFY_DAYS,
                    default=current.get(
                        CONF_FILTER_NOTIFY_DAYS, DEFAULT_FILTER_NOTIFY_DAYS
                    ),
                ): selector.NumberSelector(selector.NumberSelectorConfig(
                    min=1,
                    max=180,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )),
                vol.Optional(
                    CONF_FILTER_NOTIFY_SERVICE,
                    default=current.get(CONF_FILTER_NOTIFY_SERVICE, ""),
                ): str,
                vol.Optional(
                    CONF_HOST,
                    default=current.get(CONF_HOST, ""),
                ): str,
                vol.Required(
                    CONF_PORT,
                    default=current.get(CONF_PORT, DEFAULT_PORT),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                vol.Optional(
                    CONF_SERIAL_PORT,
                    default=current.get(CONF_SERIAL_PORT, ""),
                ): str,
        }
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
            errors=errors,
        )

    async def async_step_tcp(self, user_input: dict | None = None) -> FlowResult:
        current = self._current
        errors = {}
        if user_input is not None:
            try:
                await PassiveLinkClient(
                    user_input[CONF_HOST], user_input[CONF_PORT], lambda _: None
                ).probe()
            except (OSError, ConnectionError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_CONNECTION_TYPE: CONNECTION_TCP,
                        **user_input,
                        **self._notification_options,
                    },
                )
        return self.async_show_form(
            step_id="tcp",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=current.get(CONF_HOST, "")): str,
                vol.Required(
                    CONF_PORT, default=current.get(CONF_PORT, DEFAULT_PORT)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            }),
            errors=errors,
        )

    async def async_step_serial(self, user_input: dict | None = None) -> FlowResult:
        current = self._current
        errors = {}
        if user_input is not None:
            try:
                await PassiveSerialClient(
                    user_input[CONF_SERIAL_PORT], lambda _: None
                ).probe()
            except (OSError, ConnectionError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_CONNECTION_TYPE: CONNECTION_SERIAL,
                        **user_input,
                        **self._notification_options,
                    },
                )
        return self.async_show_form(
            step_id="serial",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_SERIAL_PORT, default=current.get(CONF_SERIAL_PORT, "")
                ): str
            }),
            errors=errors,
        )
