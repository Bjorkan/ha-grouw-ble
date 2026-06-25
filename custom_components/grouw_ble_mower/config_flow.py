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
    CONF_PIN,
    DAYE_SERVICE_UUIDS,
    DEFAULT_NAME,
    DOMAIN,
    SUPPORTED_LOCAL_NAME_PREFIXES,
)

PIN_LENGTH = 4


def _normalize_address(address: str) -> str:
    return address.strip().upper()


def _is_valid_address(address: str) -> bool:
    """Return true when the manual setup address is not blank."""
    return bool(_normalize_address(address))


def _is_supported_bluetooth_name(name: str) -> bool:
    """Return true for BLE local names used by supported mower apps/devices."""
    return name.startswith(SUPPORTED_LOCAL_NAME_PREFIXES)


def _is_valid_pin(pin: str) -> bool:
    """Return true for a blank PIN or the Daye app's 4-digit PIN shape."""
    return pin == "" or (len(pin) == PIN_LENGTH and pin.isascii() and pin.isdecimal())


def _has_supported_service_uuid(service_uuids: list[str] | tuple[str, ...]) -> bool:
    """Return true if a discovery includes a confirmed Daye mower service UUID."""
    supported = {uuid.lower() for uuid in DAYE_SERVICE_UUIDS}
    return any(uuid.lower() in supported for uuid in service_uuids)


def _is_supported_bluetooth_service_info(
    info: bluetooth.BluetoothServiceInfoBleak,
) -> bool:
    """Return true for supported Daye mower Bluetooth discoveries."""
    name = info.name or info.local_name or ""
    return _is_supported_bluetooth_name(name) or _has_supported_service_uuid(
        tuple(info.service_uuids or ())
    )


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
            self._discovery_info = None
            return await self.async_step_pin(
                user_input={
                    CONF_ADDRESS: address,
                    CONF_NAME: user_input.get(CONF_NAME) or name,
                }
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

    async def async_step_pin(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for the mower PIN code."""
        if user_input is not None:
            if CONF_ADDRESS in user_input:
                self.context["pin_data"] = {
                    CONF_ADDRESS: user_input[CONF_ADDRESS],
                    CONF_NAME: user_input.get(CONF_NAME, DEFAULT_NAME),
                }
                return self.async_show_form(
                    step_id="pin",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_PIN, default=""): str,
                        }
                    ),
                    description_placeholders={
                        "name": user_input.get(CONF_NAME, DEFAULT_NAME),
                    },
                )

            pin = user_input.get(CONF_PIN, "").strip()
            pin_data = self.context.get("pin_data", {})
            if not pin_data:
                return self.async_abort(reason="missing_data")
            if not _is_valid_pin(pin):
                return self.async_show_form(
                    step_id="pin",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_PIN, default=pin): str,
                        }
                    ),
                    errors={CONF_PIN: "invalid_pin"},
                    description_placeholders={
                        "name": pin_data.get(CONF_NAME, DEFAULT_NAME),
                    },
                )
            return self.async_create_entry(
                title=pin_data.get(CONF_NAME, DEFAULT_NAME),
                data={
                    CONF_ADDRESS: pin_data[CONF_ADDRESS],
                    CONF_NAME: pin_data.get(CONF_NAME, DEFAULT_NAME),
                    CONF_PIN: pin,
                },
            )

        return self.async_abort(reason="missing_data")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = _normalize_address(user_input[CONF_ADDRESS])
            if not _is_valid_address(address):
                errors[CONF_ADDRESS] = "invalid_address"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                return await self.async_step_pin(
                    user_input={
                        CONF_ADDRESS: address,
                        CONF_NAME: user_input.get(CONF_NAME) or DEFAULT_NAME,
                    }
                )

        current = bluetooth.async_discovered_service_info(self.hass, connectable=True)
        choices: list[selector.SelectOptionDict] = []
        for info in current:
            name = info.name or info.local_name or ""
            if _is_supported_bluetooth_service_info(info):
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
