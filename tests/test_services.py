"""Tests for integration service action routing."""
from __future__ import annotations

import asyncio
from typing import Any

from custom_components.grouw_ble_mower import _async_register_services
from custom_components.grouw_ble_mower.const import (
    DOMAIN,
    SERVICE_CHANGE_PIN,
    SERVICE_GET_MOWER_SETTINGS,
    SERVICE_GET_MULTI_AREA,
    SERVICE_GET_WORK_TIMES,
    SERVICE_SEND_RAW_JSON,
    SERVICE_SET_MOWER_SETTINGS,
    SERVICE_SET_MULTI_AREA,
    SERVICE_SET_WORK_TIMES,
)
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import ServiceValidationError


class _ServiceRegistry:
    def __init__(self) -> None:
        self.handlers: dict[tuple[str, str], Any] = {}
        self.supports_response: dict[tuple[str, str], Any] = {}

    def has_service(self, domain: str, service: str) -> bool:
        return (domain, service) in self.handlers

    def async_register(
        self,
        domain: str,
        service: str,
        handler: Any,
        *,
        schema: Any = None,
        supports_response: Any = None,
    ) -> None:
        self.handlers[(domain, service)] = handler
        self.supports_response[(domain, service)] = supports_response


class _Hass:
    def __init__(self) -> None:
        self.data = {DOMAIN: {}}
        self.services = _ServiceRegistry()


class _Call:
    data: dict[str, Any] = {"payload": {"command": "status"}}


def test_send_raw_payload_requires_resolvable_target_mower() -> None:
    """The raw BLE payload action reports bad targeting as a validation error."""
    async def run() -> None:
        hass = _Hass()
        _async_register_services(hass)
        handler = hass.services.handlers[(DOMAIN, SERVICE_SEND_RAW_JSON)]

        try:
            await handler(_Call())
        except ServiceValidationError:
            return
        raise AssertionError("Expected ServiceValidationError")

    asyncio.run(run())


def test_services_are_registered_with_response_support() -> None:
    """Service actions advertise HA response support for returned pyGrouw data."""
    hass = _Hass()
    _async_register_services(hass)

    assert (
        hass.services.supports_response[(DOMAIN, SERVICE_SEND_RAW_JSON)]
        is SupportsResponse.OPTIONAL
    )
    assert (
        hass.services.supports_response[(DOMAIN, SERVICE_CHANGE_PIN)]
        is SupportsResponse.OPTIONAL
    )
    assert (
        hass.services.supports_response[(DOMAIN, SERVICE_SET_MULTI_AREA)]
        is SupportsResponse.OPTIONAL
    )
    assert (
        hass.services.supports_response[(DOMAIN, SERVICE_SET_MOWER_SETTINGS)]
        is SupportsResponse.OPTIONAL
    )
    assert (
        hass.services.supports_response[(DOMAIN, SERVICE_SET_WORK_TIMES)]
        is SupportsResponse.OPTIONAL
    )
    assert (
        hass.services.supports_response[(DOMAIN, SERVICE_GET_MULTI_AREA)]
        is SupportsResponse.OPTIONAL
    )
    assert (
        hass.services.supports_response[(DOMAIN, SERVICE_GET_MOWER_SETTINGS)]
        is SupportsResponse.OPTIONAL
    )
    assert (
        hass.services.supports_response[(DOMAIN, SERVICE_GET_WORK_TIMES)]
        is SupportsResponse.OPTIONAL
    )


def test_get_multi_area_returns_response_data() -> None:
    """Read services return pyGrouw response data for service response variables."""
    async def run() -> None:
        hass = _Hass()

        class Coordinator:
            address = "AA:BB:CC:DD:EE:FF"

            async def async_get_multi_area(self) -> dict[str, Any]:
                return {"multi_area": {"area2_percentage": 5}}

        hass.data[DOMAIN]["entry-1"] = Coordinator()
        _async_register_services(hass)
        handler = hass.services.handlers[(DOMAIN, SERVICE_GET_MULTI_AREA)]

        quiet_call = type("Call", (), {"data": {"entry_id": "entry-1"}})()
        response_call = type(
            "Call",
            (),
            {"data": {"entry_id": "entry-1"}, "return_response": True},
        )()

        assert await handler(quiet_call) is None
        assert await handler(response_call) == {"multi_area": {"area2_percentage": 5}}

    asyncio.run(run())


def test_optional_response_services_return_only_when_requested() -> None:
    """Write/debug services keep normal calls quiet and honor response requests."""
    async def run() -> None:
        hass = _Hass()

        class Coordinator:
            address = "AA:BB:CC:DD:EE:FF"

            async def async_send_raw_json(
                self, payload: dict[str, Any]
            ) -> dict[str, Any]:
                return {"cmd": 0x80, "battery_level": 42}

        hass.data[DOMAIN]["entry-1"] = Coordinator()
        _async_register_services(hass)
        handler = hass.services.handlers[(DOMAIN, SERVICE_SEND_RAW_JSON)]

        quiet_call = type(
            "Call",
            (),
            {"data": {"entry_id": "entry-1", "payload": {"command": "status"}}},
        )()
        response_call = type(
            "Call",
            (),
            {
                "data": {"entry_id": "entry-1", "payload": {"command": "status"}},
                "return_response": True,
            },
        )()

        assert await handler(quiet_call) is None
        assert await handler(response_call) == {"cmd": 0x80, "battery_level": 42}

    asyncio.run(run())


def test_change_pin_uses_configured_current_pin() -> None:
    """The public action only needs the new PIN; coordinator knows the old one."""
    async def run() -> None:
        hass = _Hass()

        class Coordinator:
            address = "AA:BB:CC:DD:EE:FF"
            new_pin: str | None = None

            async def async_change_pin(self, new_pin: str) -> dict[str, Any]:
                self.new_pin = new_pin
                return {"pin_change_success": True}

        coordinator = Coordinator()
        hass.data[DOMAIN]["entry-1"] = coordinator
        _async_register_services(hass)
        handler = hass.services.handlers[(DOMAIN, SERVICE_CHANGE_PIN)]

        call = type(
            "Call",
            (),
            {
                "data": {"entry_id": "entry-1", "new_pin": "4321"},
                "return_response": True,
            },
        )()

        assert await handler(call) == {"pin_change_success": True}
        assert coordinator.new_pin == "4321"

    asyncio.run(run())


def test_change_pin_ignores_legacy_old_pin_field() -> None:
    """Existing automations may still pass old_pin, but pyGrouw should not see it."""
    async def run() -> None:
        hass = _Hass()

        class Coordinator:
            address = "AA:BB:CC:DD:EE:FF"
            called_with: tuple[Any, ...] | None = None

            async def async_change_pin(self, *args: Any) -> dict[str, Any]:
                self.called_with = args
                return {"pin_change_success": True}

        coordinator = Coordinator()
        hass.data[DOMAIN]["entry-1"] = coordinator
        _async_register_services(hass)
        handler = hass.services.handlers[(DOMAIN, SERVICE_CHANGE_PIN)]

        call = type(
            "Call",
            (),
            {
                "data": {
                    "entry_id": "entry-1",
                    "new_pin": "4321",
                    "old_pin": "1234",
                },
                "return_response": True,
            },
        )()

        assert await handler(call) == {"pin_change_success": True}
        assert coordinator.called_with == ("4321",)

    asyncio.run(run())
