"""The DS18B20 service answers from a background reading, never from the bus."""
import json
import sys
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "gateway"))

import onewire_temperature_server as service


class SlowReader:
    """Stands in for SensorReader; each read takes as long as the real bus."""

    def __init__(self):
        self.reads = 0
        self.release = threading.Event()

    def payload(self):
        self.reads += 1
        if self.reads > 1:
            self.release.wait(5)
        return {"available": True, "flow_temperature": 30.0 + self.reads, "return_temperature": 25.0,
                "flow_sensor": "28-a", "return_sensor": "28-b"}


class CachedReaderTests(unittest.TestCase):
    def test_request_is_answered_from_the_latest_reading_while_the_bus_is_busy(self):
        reader = SlowReader()
        cache = service.CachedReader(reader, interval=0.01)
        cache.start()
        self.addCleanup(cache.stop)
        self.addCleanup(reader.release.set)
        server = ThreadingHTTPServer(("127.0.0.1", 0), service.handler_factory(cache))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        # The second read is blocked, as a slow bus would be; the answer is instant.
        url = f"http://127.0.0.1:{server.server_address[1]}/temperatures"
        payload = json.load(urllib.request.urlopen(url, timeout=1))
        self.assertTrue(payload["available"])
        self.assertEqual(payload["flow_temperature"], 31.0)
        self.assertIn("onewire_sample_age_seconds", payload)

    def test_a_stuck_reader_reports_the_temperatures_as_missing(self):
        cache = service.CachedReader(SlowReader(), interval=60)
        cache.refresh()
        with patch.object(service.time, "monotonic", return_value=cache._read_at + service.STALE_AFTER_SECONDS + 1):
            payload = cache.payload()
        self.assertFalse(payload["available"])
        self.assertIsNone(payload["flow_temperature"])
        self.assertIsNone(payload["return_temperature"])

    def test_no_reading_yet_is_unavailable(self):
        payload = service.CachedReader(SlowReader()).payload()
        self.assertEqual(payload, {"available": False, "flow_temperature": None, "return_temperature": None})

    def test_a_failing_read_keeps_the_previous_reading(self):
        reader = SlowReader()
        cache = service.CachedReader(reader)
        cache.refresh()
        reader.payload = lambda: (_ for _ in ()).throw(OSError("bus error"))
        with self.assertLogs(service.LOGGER, "ERROR"):
            cache.refresh()
        self.assertEqual(cache.payload()["flow_temperature"], 31.0)


if __name__ == "__main__":
    unittest.main()
