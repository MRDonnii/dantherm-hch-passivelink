"""Optional non-blocking water preheater temperature client."""

from __future__ import annotations

import asyncio

from aiohttp import ClientError, ClientSession


class AuxiliaryTemperatureClient:
    """Fetch optional DS18B20 values without affecting the RS485 client."""

    def __init__(self, session: ClientSession, host: str, port: int) -> None:
        self._session = session
        self._url = f"http://{host}:{port}/temperatures"

    async def async_fetch(self) -> dict[str, object] | None:
        try:
            async with asyncio.timeout(5):
                response = await self._session.get(self._url)
                response.raise_for_status()
                payload = await response.json()
        except (TimeoutError, ClientError, ValueError):
            return None
        if not isinstance(payload, dict) or not payload.get("available"):
            return None
        flow = payload.get("flow_temperature")
        return_temp = payload.get("return_temperature")
        if not isinstance(flow, (int, float)) or not isinstance(
            return_temp, (int, float)
        ):
            return None
        return {
            "preheater_flow_temperature": round(float(flow), 2),
            "preheater_return_temperature": round(float(return_temp), 2),
            "preheater_sensor_connected": True,
        }
