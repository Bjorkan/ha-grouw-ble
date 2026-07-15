"""Config flow for Grouw Mower."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pygrouw import (
    has_supported_service_uuid,
    is_supported_bluetooth_name,
    is_valid_pin,
    normalize_address,
)
import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import CONF_ADDRESS, CONF_PIN, DEFAULT_NAME, DOMAIN


def _normalize_address(address: str) -> str:
    return normalize_address(address)


def _is_valid_address(address: str) -> bool:
    """Return true when the manual setup address is not blank."""
    return bool(_normalize_address(address))


def _is_supported_bluetooth_name(name: str) -> bool:
    """Return true for BLE local names used by supported mower apps/devices."""
    return is_supported_bluetooth_name(name)


def _is_valid_pin(pin: str) -> bool:
    """Return true for the Daye app's required 4-digit PIN shape."""
    return is_valid_pin(pin)


def _has_supported_service_uuid(service_uuids: list[str] | tuple[str, ...]) -> bool:
    """Return true if a discovery includes a confirmed Daye mower service UUID."""
    return has_supported_service_uuid(service_uuids)


def _is_supported_bluetooth_service_info(
    info: bluetooth.BluetoothServiceInfoBleak,
) -> bool:
    """Return true for supported Daye mower Bluetooth discoveries."""
    name = info.name or info.local_name or ""
    return _is_supported_bluetooth_name(name) or _has_supported_service_uuid(
        tuple(info.service_uuids or ())
    )


class GrouwBleMowerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Grouw Mower."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: bluetooth.BluetoothServiceInfoBleak | None = None

    def _pin_form(
        self,
        step_id: str,
        name: str,
        default_pin: str = "",
        errors: dict[str, str] | None = None,
    ) -> FlowResult:
        """Show a PIN entry form."""
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PIN, default=default_pin): str,
                }
            ),
            errors=errors or {},
            description_placeholders={"name": name},
        )

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
            self._discovery_info.name or self._discovery_info.local_name or DEFAULT_NAME
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
                return self._pin_form("pin", user_input.get(CONF_NAME, DEFAULT_NAME))

            pin = user_input.get(CONF_PIN, "").strip()
            pin_data = self.context.get("pin_data", {})
            if not pin_data:
                return self.async_abort(reason="missing_data")
            if not _is_valid_pin(pin):
                return self._pin_form(
                    "pin",
                    pin_data.get(CONF_NAME, DEFAULT_NAME),
                    default_pin=pin,
                    errors={CONF_PIN: "invalid_pin"},
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

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle reauthentication after a mower PIN/auth failure."""
        address = _normalize_address(entry_data[CONF_ADDRESS])
        name = entry_data.get(CONF_NAME, DEFAULT_NAME)
        self.context["pin_data"] = {
            CONF_ADDRESS: address,
            CONF_NAME: name,
        }
        self.context["title_placeholders"] = {"name": name}
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask the user for the current mower PIN."""
        reauth_entry = self._get_reauth_entry()
        pin_data = self.context.get("pin_data") or {
            CONF_ADDRESS: _normalize_address(reauth_entry.data[CONF_ADDRESS]),
            CONF_NAME: reauth_entry.data.get(CONF_NAME, DEFAULT_NAME),
        }
        name = pin_data.get(CONF_NAME, DEFAULT_NAME)

        if user_input is not None:
            pin = user_input.get(CONF_PIN, "").strip()
            if not _is_valid_pin(pin):
                return self._pin_form(
                    "reauth_confirm",
                    name,
                    default_pin=pin,
                    errors={CONF_PIN: "invalid_pin"},
                )

            await self.async_set_unique_id(pin_data[CONF_ADDRESS])
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(
                reauth_entry,
                data_updates={CONF_PIN: pin},
            )

        return self._pin_form("reauth_confirm", name)

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
