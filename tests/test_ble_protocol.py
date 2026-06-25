"""Tests for Grouw/Daye BLE framing."""
from __future__ import annotations

from custom_components.grouw_ble_mower.ble_protocol import (
    DAYE_STATUS_REQUEST,
    encode_daye_command,
    encode_daye_session_start,
    encode_raw_payload,
    parse_daye_payload,
)


def test_encode_daye_command_returns_captured_status_poll() -> None:
    """The status poll matches the payload captured from the Daye app."""
    assert encode_daye_command("status") == DAYE_STATUS_REQUEST


def test_encode_daye_session_start_contains_current_time_payload() -> None:
    """The session start payload uses the captured DYM time-sync shape."""
    from datetime import datetime

    payload = encode_daye_session_start(datetime(2026, 6, 25, 18, 28))

    assert payload.hex() == "44594d02141a0619121c000000000000000000160601ff0a"


def test_encode_raw_payload_accepts_hex_and_command() -> None:
    """The debug service can send raw hex or a named captured command."""
    assert encode_raw_payload({"raw_hex": "44 59 4d"}) == b"DYM"
    assert encode_raw_payload({"command": "dock"}) == encode_daye_command("dock")
    assert encode_raw_payload({"command": "resume"}).hex().startswith("44594d0100")


def test_parse_daye_status_notification_maps_observed_fields() -> None:
    """Parse battery and mode bytes observed in the HCI snoop log."""
    message = parse_daye_payload(
        bytes.fromhex("44594d8064331b010004000100444100000000160601")
    )

    assert message == {
        "raw_hex": "44594d8064331b010004000100444100000000160601",
        "cmd": 0x80,
        "trailer": "160601",
        "power": 0x64,
        "mode": 0x00,
        "station": True,
    }
