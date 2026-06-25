"""Tests for Grouw BLE JSON framing."""
from __future__ import annotations

from custom_components.grouw_ble_mower.ble_protocol import (
    HEADER,
    encode_json_frame,
    extract_payloads,
    parse_payload,
)


def test_encode_json_frame_uses_experimental_header_length_and_checksum() -> None:
    """A short JSON payload is framed with the experimental BLE JSON transport."""
    packets = encode_json_frame({"probe": "daye"})

    assert len(packets) == 1
    packet = packets[0]
    payload = b'{"probe":"daye"}'
    checksum = 0
    for byte in payload:
        checksum ^= byte

    assert packet == bytes(
        [HEADER, len(payload) & 0xFF, (len(payload) >> 8) & 0xFF, checksum]
    ) + payload


def test_extract_payloads_reassembles_chunked_notifications() -> None:
    """Notifications split on BLE packet boundaries are reassembled."""
    packets = encode_json_frame({"probe": "x" * 60})
    buffer = bytearray()
    payloads = []

    for packet in packets:
        buffer.extend(packet)
        payloads.extend(extract_payloads(buffer))

    assert len(packets) > 1
    assert len(payloads) == 1
    assert parse_payload(payloads[0]) == {"probe": "x" * 60}
    assert buffer == bytearray()


def test_extract_payloads_discards_bad_checksum_and_resynchronizes() -> None:
    """A corrupt frame is discarded without poisoning the next valid frame."""
    bad = bytearray(encode_json_frame({"probe": "bad"})[0])
    bad[3] ^= 0xFF
    good = b"".join(encode_json_frame({"probe": "good"}))
    buffer = bytearray(b"\x00\x01") + bad + bytearray(good)

    payloads = extract_payloads(buffer)

    assert [parse_payload(payload) for payload in payloads] == [
        {"probe": "good"}
    ]
    assert buffer == bytearray()
