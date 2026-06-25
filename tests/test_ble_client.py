"""Tests for Grouw/Daye BLE client helpers."""
from __future__ import annotations

import asyncio

import pytest

from custom_components.grouw_ble_mower.ble_client import (
    GrouwBleAuthenticationError,
    GrouwBleMowerClient,
)
from custom_components.grouw_ble_mower.ble_protocol import DAYE_RESPONSE_PIN_OR_AUTH


class _Hass:
    """Minimal Home Assistant stub for client construction."""


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
