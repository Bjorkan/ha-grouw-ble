"""Experimental BLE framing and JSON parsing for Grouw/Daye mower devices."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

HEADER = 0xA4
POCKET_LENGTH = 20
FIRST_PACKET_PAYLOAD_LENGTH = 16


def _xor(data: bytes) -> int:
    """Return the XOR checksum used by the experimental BLE JSON transport."""
    value = 0
    for byte in data:
        value ^= byte
    return value & 0xFF


def encode_json_frame(payload: dict[str, Any]) -> list[bytes]:
    """Encode a JSON payload into one or more BLE writes."""
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    length = len(body)
    frame = bytearray((HEADER, length & 0xFF, (length >> 8) & 0xFF, _xor(body)))
    frame.extend(body)

    if len(frame) <= POCKET_LENGTH:
        return [bytes(frame)]

    packets: list[bytes] = [bytes(frame[:POCKET_LENGTH])]
    offset = POCKET_LENGTH
    while offset < len(frame):
        packets.append(bytes(frame[offset : offset + POCKET_LENGTH]))
        offset += POCKET_LENGTH
    return packets


def extract_payloads(buffer: bytearray) -> list[bytes]:
    """Extract complete payloads from a notification byte stream."""
    payloads: list[bytes] = []

    while True:
        try:
            header_pos = buffer.index(HEADER)
        except ValueError:
            buffer.clear()
            return payloads

        if header_pos:
            del buffer[:header_pos]

        if len(buffer) < 4:
            return payloads

        length = buffer[1] | (buffer[2] << 8)
        total_length = 4 + length
        if len(buffer) < total_length:
            return payloads

        checksum = buffer[3]
        payload = bytes(buffer[4:total_length])
        del buffer[:total_length]

        if _xor(payload) != checksum:
            _LOGGER.warning("Discarding BLE frame with invalid checksum")
            continue

        payloads.append(payload)


def parse_payload(payload: bytes) -> dict[str, Any] | None:
    """Parse a UTF-8 JSON BLE payload."""
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _LOGGER.debug("Ignoring non-JSON BLE payload: %s", payload.hex())
        return None

    if not isinstance(data, dict):
        return None
    return data


def _optional_int(data: dict[str, Any], key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(slots=True, frozen=True)
class MowerState:
    """Latest parsed mower state."""

    address: str
    name: str | None = None
    model: str | None = None
    serial: str | None = None
    firmware_version: str | None = None
    power: int | None = None
    mode: int | None = None
    error_type: int | None = None
    station: bool | None = None
    wifi_level: int | None = None
    rain_enabled: bool | None = None
    rain_status: int | None = None
    rain_delay_left: int | None = None
    rain_delay_set: int | None = None
    on_min: int | None = None
    total_min: int | None = None
    on_area: int | None = None
    cur_min: int | None = None
    cur_area: int | None = None
    led_enabled: bool | None = None
    ultrasonic_enabled: bool | None = None
    last_command_result: bool | None = None
    last_command: int | None = None
    last_response_cmd: int | None = None
    raw: dict[str, Any] | None = None
    last_seen: datetime | None = None

    @property
    def available(self) -> bool:
        return self.last_seen is not None


def state_from_message(
    address: str,
    message: dict[str, Any],
    previous: MowerState | None = None,
) -> MowerState:
    """Update a state object from a parsed BLE JSON message.

    Daye status payload fields are not confirmed yet. Until they are, preserve
    the raw message and response command only instead of mapping old app fields
    into user-facing entity state.
    """
    base = previous or MowerState(address=address)
    cmd = _optional_int(message, "cmd")
    updates: dict[str, Any] = {
        "raw": message,
        "last_response_cmd": cmd,
        "last_seen": datetime.now(timezone.utc),
    }

    return replace(base, **updates)
