"""Optional non-blocking water preheater temperature client."""

from __future__ import annotations

import asyncio

from aiohttp import ClientError, ClientSession

from .const import PI_DIAGNOSTIC_KEYS


class AuxiliaryTemperatureClient:
    """Fetch optional DS18B20 and Raspberry Pi diagnostic values.

    The two are independent: a Pi without DS18B20 sensors attached can still
    report host diagnostics, and vice versa. Neither affects the RS485 client.
    """

    def __init__(
        self, session: ClientSession, host: str, port: int, *, swap_sensors: bool
    ) -> None:
        self._session = session
        self._url = f"http://{host}:{port}/temperatures"
        self._swap_sensors = swap_sensors

    async def async_fetch(self) -> dict[str, object] | None:
        try:
            async with asyncio.timeout(5):
                response = await self._session.get(self._url)
                response.raise_for_status()
                payload = await response.json()
        except (TimeoutError, ClientError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        result: dict[str, object] = {}
        flow = payload.get("flow_temperature")
        return_temp = payload.get("return_temperature")
        if (
            payload.get("available")
            and isinstance(flow, (int, float))
            and isinstance(return_temp, (int, float))
        ):
            if self._swap_sensors:
                flow, return_temp = return_temp, flow
            result.update(
                preheater_flow_temperature=round(float(flow), 2),
                preheater_return_temperature=round(float(return_temp), 2),
                preheater_sensor_connected=True,
            )
        if payload.get("pi_diagnostics_available"):
            result.update((key, payload.get(key)) for key in PI_DIAGNOSTIC_KEYS)
        return result or None
