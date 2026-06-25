"""Tests for integration service action routing."""
from __future__ import annotations

import asyncio
from typing import Any

from custom_components.grouw_ble_mower import _async_register_services
from custom_components.grouw_ble_mower.const import DOMAIN, SERVICE_SEND_RAW_JSON
from homeassistant.exceptions import ServiceValidationError


class _ServiceRegistry:
    def __init__(self) -> None:
        self.handlers: dict[tuple[str, str], Any] = {}

    def has_service(self, domain: str, service: str) -> bool:
        return (domain, service) in self.handlers

    def async_register(
        self,
        domain: str,
        service: str,
        handler: Any,
        *,
        schema: Any = None,
    ) -> None:
        self.handlers[(domain, service)] = handler


class _Hass:
    def __init__(self) -> None:
        self.data = {DOMAIN: {}}
        self.services = _ServiceRegistry()


class _Call:
    data: dict[str, Any] = {"payload": {"probe": "daye"}}


def test_send_raw_json_requires_resolvable_target_mower() -> None:
    """The raw JSON action reports bad targeting as a validation error."""
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
