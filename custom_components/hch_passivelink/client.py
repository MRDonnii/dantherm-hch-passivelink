"""Receive-only TCP client."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from .parser import DanthermDecoder, RtuStreamParser

_LOGGER = logging.getLogger(__name__)


class PassiveLinkClient:
    """Continuously receive a raw RTU-over-TCP stream without ever writing."""

    def __init__(self, host: str, port: int, update: Callable[[dict[str, object]], None]) -> None:
        self.host, self.port, self._update = host, port, update
        self.decoder = DanthermDecoder(update)
        self.parser = RtuStreamParser(self.decoder.decode)
        self._stopped = False
        self.connected = False

    async def probe(self, timeout: float = 8) -> None:
        """Verify that the endpoint yields at least one valid decoded update."""
        event = asyncio.Event()
        decoder = DanthermDecoder(lambda _: event.set())
        parser = RtuStreamParser(decoder.decode)
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port), timeout=timeout
        )
        try:
            async with asyncio.timeout(timeout):
                while not event.is_set():
                    chunk = await reader.read(4096)
                    if not chunk:
                        raise ConnectionError("TCP stream closed")
                    parser.feed(chunk)
        finally:
            writer.close()
            await writer.wait_closed()

    async def run(self) -> None:
        delay = 1
        while not self._stopped:
            writer = None
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
                self.connected, delay = True, 1
                self._update(dict(self.decoder.data))
                while not self._stopped:
                    try:
                        chunk = await asyncio.wait_for(reader.read(4096), timeout=15)
                    except asyncio.TimeoutError as err:
                        self.decoder._set(bus_traffic=False)
                        raise ConnectionError("No RS485 traffic for 15 seconds") from err
                    if not chunk:
                        raise ConnectionError("TCP stream closed")
                    self.parser.feed(chunk)
            except (OSError, ConnectionError) as err:
                self.connected = False
                self._update(dict(self.decoder.data))
                _LOGGER.debug("PassiveLink reconnect: %s", err)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)
            finally:
                if writer is not None:
                    writer.close()
                    await writer.wait_closed()

    async def stop(self) -> None:
        self._stopped = True
