import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "hch_passivelink"))

from parser import DanthermDecoder, RtuStreamParser, crc16


def frame(body: bytes) -> bytes:
    return body + crc16(body).to_bytes(2, "little")


def test_fragmented_temperature_response():
    updates = []
    decoder = DanthermDecoder(updates.append)
    parser = RtuStreamParser(decoder.decode)
    body = bytes.fromhex("0104080576094c083705a2")
    message = frame(body)
    parser.feed(message[:4])
    parser.feed(message[4:])
    assert decoder.data["outdoor_temperature"] == 13.98
    assert decoder.data["supply_temperature"] == 23.80
    assert decoder.data["extract_temperature"] == 21.03
    assert decoder.data["exhaust_temperature"] == 14.42


def test_fan_registers_and_mode():
    decoder = DanthermDecoder(lambda _: None)
    decoder.decode(frame(bytes.fromhex("010600420019")))
    decoder.decode(frame(bytes.fromhex("01060043000d")))
    assert decoder.data["extract_fan_percent"] == 25
    assert decoder.data["supply_fan_percent"] == 13
    assert decoder.data["current_level"] == "level_1"


def test_bad_crc_is_ignored():
    decoder = DanthermDecoder(lambda _: None)
    parser = RtuStreamParser(decoder.decode)
    parser.feed(bytes.fromhex("0106004200190000"))
    assert "extract_fan_percent" not in decoder.data


def test_write_multiple_request_is_kept_as_one_frame():
    frames = []
    parser = RtuStreamParser(frames.append)
    body = bytes.fromhex("401000b400050a00150016800080000000")
    message = frame(body)
    parser.feed(message[:8])
    parser.feed(message[8:])
    assert frames == [message]


def test_supply_air_setpoint_from_hac1_write_block():
    decoder = DanthermDecoder(lambda _: None)
    body = bytes.fromhex("401000b900050aff011600000f18fee201")
    decoder.decode(frame(body))
    assert decoder.data["afterheat_setpoint"] == 22


def test_tcp_client_callback_can_be_rebound():
    import types

    package = types.ModuleType("hch_passivelink")
    package.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "hch_passivelink")]
    sys.modules.setdefault("hch_passivelink", package)
    from hch_passivelink.client import PassiveLinkClient

    initial = []
    rebound = []
    client = PassiveLinkClient("127.0.0.1", 4196, initial.append)
    client.set_update_callback(rebound.append)
    client.decoder.decode(frame(bytes.fromhex("010600420019")))
    assert initial == []
    assert rebound[-1]["extract_fan_percent"] == 25
