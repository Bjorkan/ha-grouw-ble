"""Tests for Grouw/Daye BLE framing."""
from __future__ import annotations

from custom_components.grouw_ble_mower.ble_protocol import (
    DAYE_STATUS_REQUEST,
    MowerState,
    encode_daye_command,
    encode_daye_session_start,
    encode_raw_payload,
    parse_daye_payload,
    redact_daye_message,
    state_from_message,
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
        "battery_level": 0x64,
        "mode": 0x00,
        "station": True,
    }


def test_parse_daye_payload_ignores_non_dym_payload() -> None:
    """Non-Daye notifications are ignored."""
    assert parse_daye_payload(bytes.fromhex("01020304")) is None


def test_parse_daye_payload_does_not_decode_short_status_payload() -> None:
    """Only the captured 22-byte DYM status shape is decoded as state."""
    message = parse_daye_payload(bytes.fromhex("44594d806400160601"))

    assert message == {
        "raw_hex": "44594d806400160601",
        "cmd": 0x80,
        "trailer": "160601",
    }


def test_parse_daye_auth_response_extracts_numeric_pin_digits() -> None:
    """The auth/PIN response exposes the mower PIN as four digit bytes."""
    message = parse_daye_payload(
        bytes.fromhex("44594d8c0102030400000000000000000000160601")
    )

    assert message == {
        "raw_hex": "44594d8c0102030400000000000000000000160601",
        "cmd": 0x8C,
        "trailer": "160601",
        "mower_pin": "1234",
    }


def test_redact_daye_message_hides_pin_and_auth_pin_bytes() -> None:
    """PIN values must not leak into diagnostics or normal debug logs."""
    redacted = redact_daye_message(
        {
            "raw_hex": "44594d8c0102030400000000000000000000160601",
            "cmd": 0x8C,
            "mower_pin": "1234",
        }
    )

    assert redacted == {
        "raw_hex": "44594d8c********00000000000000000000160601",
        "cmd": 0x8C,
        "mower_pin": "****",
    }


def test_state_from_message_maps_confirmed_dym_fields() -> None:
    """MowerState only updates fields confirmed from DYM status notifications."""
    previous = MowerState(address="AA:BB:CC:DD:EE:FF", battery_level=50)

    state = state_from_message(
        "AA:BB:CC:DD:EE:FF",
        {"cmd": 0x80, "battery_level": 75, "mode": 0x14, "station": False},
        previous,
    )

    assert state.battery_level == 75
    assert state.mode == 0x14
    assert state.station is False
    assert state.last_response_cmd == 0x80
    assert state.last_seen is not None
