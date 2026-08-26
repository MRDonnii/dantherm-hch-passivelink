"""Config flow for HCH PassiveLink."""

from __future__ import annotations

import asyncio
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .client import PassiveLinkClient
from .const import DEFAULT_NAME, DEFAULT_PORT, DOMAIN


class PassiveLinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
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
                return self.async_create_entry(title=DEFAULT_NAME, data=user_input)
        schema = vol.Schema({
            vol.Required(CONF_HOST, default="10.0.0.11"): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

