"""Tests for Grouw/Daye BLE client helpers."""
from __future__ import annotations

import asyncio

import pytest

from custom_components.grouw_ble_mower.ble_client import (
    GrouwBleAuthenticationError,
    GrouwBleError,
    GrouwBleMowerClient,
    _coerce_bool,
    _coerce_expected_cmd,
    _drain_queue,
)
from custom_components.grouw_ble_mower.ble_protocol import DAYE_RESPONSE_PIN_OR_AUTH
from custom_components.grouw_ble_mower.const import DEFAULT_REQUESTED_MTU


class _Hass:
    """Minimal Home Assistant stub for client construction."""


def test_drain_queue_discards_stale_notifications() -> None:
    """Queued notifications can be discarded at request phase boundaries."""
    queue: asyncio.Queue[dict[str, int]] = asyncio.Queue()
    queue.put_nowait({"cmd": 0x80})
    queue.put_nowait({"cmd": 0x8C})

    _drain_queue(queue)

    assert queue.empty()


def test_coerce_bool_accepts_common_service_payload_strings() -> None:
    """Raw service boolean options may arrive as strings."""
    assert _coerce_bool(True)
    assert _coerce_bool("true")
    assert not _coerce_bool(False)
    assert not _coerce_bool("false")
    assert not _coerce_bool("0")
    assert _coerce_bool("yes")
    assert not _coerce_bool("off")
    with pytest.raises(GrouwBleError, match="authenticate"):
        _coerce_bool("flase")


def test_coerce_expected_cmd_accepts_hex_strings_and_validates_range() -> None:
    """Raw service expected command options are parsed as command bytes."""
    assert _coerce_expected_cmd(None) is None
    assert _coerce_expected_cmd("0x80") == 0x80
    assert _coerce_expected_cmd("128") == 128
    assert _coerce_expected_cmd(0x8C) == 0x8C

    with pytest.raises(GrouwBleError, match="between 0 and 255"):
        _coerce_expected_cmd("0x100")
    with pytest.raises(GrouwBleError, match="integer command byte"):
        _coerce_expected_cmd("eighty")


def test_wait_for_response_skips_unexpected_notifications() -> None:
    """The BLE client waits for the expected DYM command byte."""

    async def run() -> None:
        client = GrouwBleMowerClient(
            _Hass(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        client._tx_id = 1
        queue: asyncio.Queue[dict[str, int]] = asyncio.Queue()
        queue.put_nowait({"cmd": 0x80})
        queue.put_nowait({"cmd": DAYE_RESPONSE_PIN_OR_AUTH})

        message = await client._wait_for_response(
            queue,
            DAYE_RESPONSE_PIN_OR_AUTH,
            0.1,
            "auth",
        )

        assert message == {"cmd": DAYE_RESPONSE_PIN_OR_AUTH}

    asyncio.run(run())


def test_verify_auth_response_accepts_matching_configured_pin() -> None:
    """A configured PIN is checked against the mower auth response."""
    client = GrouwBleMowerClient(
        _Hass(), "AA:BB:CC:DD:EE:FF", "Test mower", pin="1234"
    )
    client._tx_id = 1

    client._verify_auth_response({"cmd": DAYE_RESPONSE_PIN_OR_AUTH, "mower_pin": "1234"})


def test_verify_auth_response_rejects_mismatched_configured_pin() -> None:
    """A wrong configured PIN fails before command payloads are sent."""
    client = GrouwBleMowerClient(
        _Hass(), "AA:BB:CC:DD:EE:FF", "Test mower", pin="9999"
    )
    client._tx_id = 1

    with pytest.raises(GrouwBleAuthenticationError, match="does not match"):
        client._verify_auth_response(
            {"cmd": DAYE_RESPONSE_PIN_OR_AUTH, "mower_pin": "1234"}
        )


def test_verify_auth_response_requires_pin_data_when_pin_is_configured() -> None:
    """A configured PIN cannot be verified when the auth response lacks PIN data."""
    client = GrouwBleMowerClient(
        _Hass(), "AA:BB:CC:DD:EE:FF", "Test mower", pin="1234"
    )
    client._tx_id = 1

    with pytest.raises(GrouwBleAuthenticationError, match="did not include PIN"):
        client._verify_auth_response({"cmd": DAYE_RESPONSE_PIN_OR_AUTH})


def test_request_mtu_with_log_calls_supported_client() -> None:
    """The client requests the APK-observed MTU when the backend exposes it."""

    class _Client:
        mtu_size = 23

        def __init__(self) -> None:
            self.requested: list[int] = []

        async def request_mtu(self, mtu: int) -> int:
            self.requested.append(mtu)
            self.mtu_size = mtu
            return mtu

    async def run() -> None:
        client = GrouwBleMowerClient(
            _Hass(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        client._tx_id = 1
        ble_client = _Client()

        await client._request_mtu_with_log(ble_client)  # type: ignore[arg-type]

        assert ble_client.requested == [DEFAULT_REQUESTED_MTU]
        assert ble_client.mtu_size == DEFAULT_REQUESTED_MTU

    asyncio.run(run())


def test_request_mtu_with_log_ignores_unsupported_client() -> None:
    """MTU negotiation is optional because Bleak backends differ."""

    class _Client:
        mtu_size = 23

    async def run() -> None:
        client = GrouwBleMowerClient(
            _Hass(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        client._tx_id = 1

        await client._request_mtu_with_log(_Client())  # type: ignore[arg-type]

    asyncio.run(run())


def test_raw_payload_accepts_hex_expected_command_and_string_auth_flag() -> None:
    """Raw service options support hex command strings and string booleans."""

    async def run() -> None:
        client = GrouwBleMowerClient(
            _Hass(), "AA:BB:CC:DD:EE:FF", "Test mower"
        )
        seen: dict[str, object] = {}

        async def fake_request(
            payload: bytes,
            *,
            authenticate: bool = True,
            expected_cmd: int | None = None,
            **kwargs: object,
        ) -> dict[str, int]:
            seen["payload"] = payload
            seen["authenticate"] = authenticate
            seen["expected_cmd"] = expected_cmd
            return {"cmd": 0x80}

        client.async_request_daye = fake_request  # type: ignore[method-assign]

        await client.async_send_raw_json(
            {
                "raw_hex": "44594d",
                "authenticate": "false",
                "expect_cmd": "0x80",
            }
        )

        assert seen == {
            "payload": b"DYM",
            "authenticate": False,
            "expected_cmd": 0x80,
        }

    asyncio.run(run())
