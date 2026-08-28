#!/usr/bin/env python3
"""Optional read-only DS18B20 HTTP service for PassiveLink."""

from __future__ import annotations

import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOGGER = logging.getLogger("passivelink-onewire")


class SensorReader:
    def __init__(self, config_path: str) -> None:
        try:
            config = json.loads(Path(config_path).read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, ValueError):
            config = {}
        self.flow_id = self._normalise(config.get("flow_sensor"))
        self.return_id = self._normalise(config.get("return_sensor"))

    @staticmethod
    def _normalise(value: object) -> str | None:
        if not value:
            return None
        return str(value).lower().removeprefix("0x")

    def _sensor_ids(self) -> tuple[str | None, str | None]:
        discovered = sorted(
            path.name
            for path in Path("/sys/bus/w1/devices").glob("28-*")
            if (path / "w1_slave").exists()
        )
        configured = [self.flow_id, self.return_id]
        if all(sensor_id in discovered for sensor_id in configured):
            return self.flow_id, self.return_id
        if len(discovered) >= 2:
            return discovered[0], discovered[1]
        return None, None

    @staticmethod
    def _read(sensor_id: str) -> float | None:
        path = Path("/sys/bus/w1/devices") / sensor_id / "w1_slave"
        try:
            lines = path.read_text(encoding="ascii").splitlines()
            if len(lines) < 2 or not lines[0].strip().endswith("YES"):
                return None
            marker = "t="
            position = lines[1].find(marker)
            if position < 0:
                return None
            value = int(lines[1][position + len(marker):]) / 1000.0
            if value == 85.0 or value <= -55.0 or value >= 125.0:
                return None
            return round(value, 2)
        except (FileNotFoundError, OSError, ValueError):
            return None

    def payload(self) -> dict[str, object]:
        flow_id, return_id = self._sensor_ids()
        flow = self._read(flow_id) if flow_id else None
        return_temp = self._read(return_id) if return_id else None
        return {
            "available": flow is not None and return_temp is not None,
            "flow_temperature": flow,
            "return_temperature": return_temp,
            "flow_sensor": flow_id,
            "return_sensor": return_id,
        }


def handler_factory(reader: SensorReader):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in ("/temperatures", "/health"):
                self.send_error(404)
                return
            payload = reader.payload()
            body = json.dumps(payload, separators=(",", ":")).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format_: str, *args) -> None:
            LOGGER.debug(format_, *args)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/etc/dantherm-passivelink/onewire.json")
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=4197)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    reader = SensorReader(args.config)
    server = ThreadingHTTPServer((args.bind, args.port), handler_factory(reader))
    LOGGER.info("Optional DS18B20 service listening on %s:%d", args.bind, args.port)
    server.serve_forever()


if __name__ == "__main__":
    main()
