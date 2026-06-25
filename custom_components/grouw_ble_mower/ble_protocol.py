"""BLE framing and parsing for Grouw/Daye mower devices."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

DYM_PREFIX = b"DYM"
DYM_TRAILER = bytes.fromhex("160601ff0a")
DYM_NOTIFICATION_TRAILER = bytes.fromhex("160601")

DAYE_STATUS_REQUEST = bytes.fromhex(
    "44594d00111111111111111100000000000000160601ff0a"
)
DAYE_START_MOWING = bytes.fromhex(
    "44594d01020000000000000000000000000000160601ff0a"
)
DAYE_PAUSE_MOWING = bytes.fromhex(
    "44594d01010000000000000000000000000000160601ff0a"
)
DAYE_DOCK = bytes.fromhex("44594d01030000000000000000000000000000160601ff0a")

DAYE_RESPONSE_PIN_OR_AUTH = 0x8C
DAYE_RESPONSE_STATUS = 0x80


def encode_daye_command(command: str) -> bytes:
    """Return a Daye command payload captured from the official app."""
    if command == "status":
        return DAYE_STATUS_REQUEST
    if command == "start":
        return DAYE_START_MOWING
    if command == "pause":
        return DAYE_PAUSE_MOWING
    if command == "dock":
        return DAYE_DOCK
    raise ValueError(f"Unsupported Daye command: {command}")


def encode_raw_payload(payload: dict[str, Any]) -> bytes:
    """Encode a raw debug payload for the Daye BLE characteristic."""
    raw_hex = payload.get("raw_hex")
    if raw_hex is not None:
        return bytes.fromhex(str(raw_hex).replace(" ", ""))

    command = payload.get("command")
    if command is not None:
        return encode_daye_command(str(command))

    raise ValueError("Payload must contain raw_hex or command")


def parse_daye_payload(payload: bytes) -> dict[str, Any] | None:
    """Parse a Daye DYM notification payload."""
    if not payload:
        return None
    if not payload.startswith(DYM_PREFIX):
        _LOGGER.debug("Ignoring non-Daye BLE payload: %s", payload.hex())
        return None

    message: dict[str, Any] = {
        "raw_hex": payload.hex(),
        "cmd": payload[3] if len(payload) > 3 else None,
    }
    if payload.endswith(DYM_NOTIFICATION_TRAILER):
        message["trailer"] = payload[-3:].hex()

    # Status notifications captured from the official app are 22 bytes:
    # 44 59 4d 80 <battery> ... <mode> 44 41 ... 16 06 01.
    if len(payload) >= 16 and payload[3] == DAYE_RESPONSE_STATUS:
        message.update(
            {
                "power": payload[4],
                "mode": payload[12],
                "station": payload[12] == 0x14,
            }
        )
    return message


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
    """Update a state object from a parsed Daye BLE message."""
    base = previous or MowerState(address=address)
    cmd = _optional_int(message, "cmd")
    updates: dict[str, Any] = {
        "raw": message,
        "last_response_cmd": cmd,
        "last_seen": datetime.now(timezone.utc),
    }

    for src, dst in (
        ("power", "power"),
        ("mode", "mode"),
    ):
        value = _optional_int(message, src)
        if value is not None:
            updates[dst] = value

    station = message.get("station")
    if isinstance(station, bool):
        updates["station"] = station

    return replace(base, **updates)
