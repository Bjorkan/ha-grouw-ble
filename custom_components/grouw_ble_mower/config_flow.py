"""Config flow for Grouw/Daye BLE Mower."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ADDRESS,
    DEFAULT_NAME,
    DOMAIN,
    SUPPORTED_LOCAL_NAME_PREFIXES,
)


def _normalize_address(address: str) -> str:
    return address.strip().upper()


def _is_supported_bluetooth_name(name: str) -> bool:
    """Return true for BLE local names used by supported mower apps/devices."""
    return name.startswith(SUPPORTED_LOCAL_NAME_PREFIXES)


class GrouwBleMowerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Grouw / Daye BLE Mower."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: bluetooth.BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle Bluetooth discovery."""
        self._discovery_info = discovery_info
        await self.async_set_unique_id(_normalize_address(discovery_info.address))
        self._abort_if_unique_id_configured()

        name = discovery_info.name or discovery_info.local_name or DEFAULT_NAME
        self.context["title_placeholders"] = {"name": name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm a Bluetooth-discovered device."""
        assert self._discovery_info is not None
        if user_input is not None:
            address = _normalize_address(self._discovery_info.address)
            name = (
                self._discovery_info.name
                or self._discovery_info.local_name
                or DEFAULT_NAME
            )
            return self.async_create_entry(
                title=user_input.get(CONF_NAME) or name,
                data={
                    CONF_ADDRESS: address,
                    CONF_NAME: user_input.get(CONF_NAME) or name,
                },
            )

        name = (
            self._discovery_info.name
            or self._discovery_info.local_name
            or DEFAULT_NAME
        )
        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=vol.Schema({vol.Optional(CONF_NAME, default=name): str}),
            description_placeholders={
                "name": name,
                "address": self._discovery_info.address,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = _normalize_address(user_input[CONF_ADDRESS])
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input.get(CONF_NAME) or DEFAULT_NAME,
                data={
                    CONF_ADDRESS: address,
                    CONF_NAME: user_input.get(CONF_NAME) or DEFAULT_NAME,
                },
            )

        current = bluetooth.async_discovered_service_info(self.hass, connectable=True)
        choices: list[selector.SelectOptionDict] = []
        for info in current:
            name = info.name or info.local_name or ""
            if _is_supported_bluetooth_name(name):
                choices.append(
                    selector.SelectOptionDict(
                        value=_normalize_address(info.address),
                        label=f"{name or DEFAULT_NAME} ({info.address})",
                    )
                )

        address_field: Any
        if choices:
            address_field = selector.SelectSelector(
                selector.SelectSelectorConfig(options=choices, custom_value=True)
            )
        else:
            address_field = str

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): address_field,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                }
            ),
            errors=errors,
        )
