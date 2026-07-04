"""Grouw Mower integration."""
from __future__ import annotations

from enum import Enum
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
try:
    from homeassistant.core import ServiceResponse, SupportsResponse
except ImportError:
    ServiceResponse = dict[str, Any]

    class SupportsResponse(Enum):
        """Fallback SupportsResponse for older Home Assistant versions."""

        OPTIONAL = "optional"

    _SUPPORTS_SERVICE_RESPONSE = False
else:
    _SUPPORTS_SERVICE_RESPONSE = True
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import UpdateFailed
from pygrouw import is_valid_pin, redact_daye_message

from .const import (
    CONF_ADDRESS,
    CONF_PIN,
    DEFAULT_NAME,
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
from .coordinator import GrouwMowerCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LAWN_MOWER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

PIN_REGEX = r"^\d{4}$"

SERVICE_SEND_RAW_JSON_SCHEMA = vol.Schema(
    {
        vol.Required("payload"): dict,
        vol.Optional("address"): cv.string,
        vol.Optional("entry_id"): cv.string,
    }
)


def _work_start_validator(value: list[int]) -> list[int]:
    """Validate a (hour, minute) pair."""
    hour, minute = value
    if not 0 <= hour <= 23:
        raise vol.Invalid(f"start hour must be between 0 and 23, got {hour}")
    if not 0 <= minute <= 59:
        raise vol.Invalid(f"start minute must be between 0 and 59, got {minute}")
    return value


def _work_duration_validator(value: list[int]) -> list[int]:
    """Validate a (hours, tenths) pair."""
    hours, tenths = value
    if not 0 <= hours <= 23:
        raise vol.Invalid(f"duration hours must be between 0 and 23, got {hours}")
    if not 0 <= tenths <= 9:
        raise vol.Invalid(f"duration tenths must be between 0 and 9, got {tenths}")
    return value


SERVICE_CHANGE_PIN_SCHEMA = vol.Schema(
    {
        vol.Required("new_pin"): vol.All(cv.string, cv.matches_regex(PIN_REGEX)),
        # Backward compatibility for existing automations; pyGrouw uses the
        # configured current PIN.
        vol.Optional("old_pin"): vol.All(cv.string, cv.matches_regex(PIN_REGEX)),
        vol.Optional("address"): cv.string,
        vol.Optional("entry_id"): cv.string,
    }
)

SERVICE_SET_MULTI_AREA_SCHEMA = vol.Schema(
    {
        vol.Required("area2_percentage"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Required("area2_distance"): vol.All(vol.Coerce(int), vol.Range(min=0, max=999)),
        vol.Required("area3_percentage"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Required("area3_distance"): vol.All(vol.Coerce(int), vol.Range(min=0, max=999)),
        vol.Optional("address"): cv.string,
        vol.Optional("entry_id"): cv.string,
    }
)

SERVICE_SET_MOWER_SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Required("mow_in_rain"): cv.boolean,
        vol.Required("boundary_cut"): cv.boolean,
        vol.Required("helix"): cv.boolean,
        vol.Required("rain_delay_hours"): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
        vol.Required("rain_delay_minutes"): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
        vol.Optional("unknown_setting", default=False): cv.boolean,
        vol.Optional("address"): cv.string,
        vol.Optional("entry_id"): cv.string,
    }
)

SERVICE_SET_WORK_TIMES_SCHEMA = vol.Schema(
    {
        vol.Required("starts"): vol.All(
            cv.ensure_list,
            vol.Length(min=7, max=7),
            [vol.All(
                cv.ensure_list,
                vol.Length(min=2, max=2),
                [vol.All(
                    vol.Coerce(int),
                    vol.Range(min=0),
                )],
                vol.Length(min=2, max=2),
                _work_start_validator,
            )]
        ),
        vol.Required("durations"): vol.All(
            cv.ensure_list,
            vol.Length(min=7, max=7),
            [vol.All(
                cv.ensure_list,
                vol.Length(min=2, max=2),
                [vol.All(
                    vol.Coerce(int),
                    vol.Range(min=0),
                )],
                vol.Length(min=2, max=2),
                _work_duration_validator,
            )]
        ),
        vol.Optional("address"): cv.string,
        vol.Optional("entry_id"): cv.string,
    }
)

SERVICE_GET_SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Optional("address"): cv.string,
        vol.Optional("entry_id"): cv.string,
    }
)


def _has_valid_configured_pin(pin: Any) -> bool:
    """Return true when the stored PIN matches the required 4-digit shape."""
    return isinstance(pin, str) and is_valid_pin(pin.strip())


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up integration-level services."""
    _async_register_services(hass)
    return True


def _resolve_coordinator(
    hass: HomeAssistant, call: ServiceCall
) -> GrouwMowerCoordinator:
    """Resolve a coordinator from service call data."""
    coordinators: dict[str, GrouwMowerCoordinator] = hass.data.get(DOMAIN, {})
    entry_id = call.data.get("entry_id")
    address = call.data.get("address")

    if entry_id:
        coordinator = coordinators.get(entry_id)
    elif address:
        address_upper = address.upper()
        coordinator = next(
            (item for item in coordinators.values() if item.address == address_upper),
            None,
        )
    elif len(coordinators) == 1:
        coordinator = next(iter(coordinators.values()))
    else:
        coordinator = None

    if coordinator is None:
        raise ServiceValidationError(
            "Could not determine target mower. Provide address or entry_id."
        )
    return coordinator


def _service_response(
    call: ServiceCall, result: dict[str, Any]
) -> ServiceResponse | None:
    """Return action response data only when the caller requested it."""
    if getattr(call, "return_response", False):
        return result
    return None


def _async_register_service(
    hass: HomeAssistant,
    service: str,
    handler: Any,
    schema: vol.Schema,
    supports_response: SupportsResponse,
) -> None:
    """Register a service with service-response support when available."""
    kwargs: dict[str, Any] = {"schema": schema}
    if _SUPPORTS_SERVICE_RESPONSE:
        kwargs["supports_response"] = supports_response

    try:
        hass.services.async_register(DOMAIN, service, handler, **kwargs)
    except TypeError:
        if "supports_response" not in kwargs:
            raise
        kwargs.pop("supports_response")
        hass.services.async_register(DOMAIN, service, handler, **kwargs)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Grouw Mower from a config entry."""
    if not _has_valid_configured_pin(entry.data.get(CONF_PIN)):
        raise ConfigEntryAuthFailed("A 4-digit mower PIN is required")

    hass.data.setdefault(DOMAIN, {})

    coordinator = GrouwMowerCoordinator(
        hass,
        entry,
        entry.data[CONF_ADDRESS],
        entry.data.get(CONF_NAME, DEFAULT_NAME),
        entry.data.get(CONF_PIN, ""),
    )
    hass.data[DOMAIN][entry.entry_id] = coordinator

    try:
        await coordinator.async_config_entry_first_refresh()
    except (ConfigEntryNotReady, UpdateFailed):
        _LOGGER.debug("Initial BLE refresh failed, continuing with unavailable entities")
        coordinator.data = None
        coordinator.last_update_success = False

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options updates."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    async def _handle_send_raw_json(call: ServiceCall) -> ServiceResponse | None:
        payload: dict[str, Any] = call.data["payload"]
        coordinator = _resolve_coordinator(hass, call)
        result = await coordinator.async_send_raw_json(payload)
        _LOGGER.info(
            "Raw BLE response from %s: %s",
            coordinator.address,
            redact_daye_message(result),
        )
        return _service_response(call, result)

    async def _handle_change_pin(call: ServiceCall) -> ServiceResponse | None:
        new_pin = call.data["new_pin"]
        coordinator = _resolve_coordinator(hass, call)
        result = await coordinator.async_change_pin(new_pin)
        _LOGGER.info("PIN changed on %s", coordinator.address)
        return _service_response(call, result)

    async def _handle_set_multi_area(call: ServiceCall) -> ServiceResponse | None:
        coordinator = _resolve_coordinator(hass, call)
        result = await coordinator.async_set_multi_area(
            area2_percentage=call.data["area2_percentage"],
            area2_distance=call.data["area2_distance"],
            area3_percentage=call.data["area3_percentage"],
            area3_distance=call.data["area3_distance"],
        )
        _LOGGER.info("Multi-area settings written to %s", coordinator.address)
        return _service_response(call, result)

    async def _handle_set_mower_settings(call: ServiceCall) -> ServiceResponse | None:
        coordinator = _resolve_coordinator(hass, call)
        result = await coordinator.async_set_mower_settings(
            mow_in_rain=call.data["mow_in_rain"],
            boundary_cut=call.data["boundary_cut"],
            helix=call.data["helix"],
            rain_delay_hours=call.data["rain_delay_hours"],
            rain_delay_minutes=call.data["rain_delay_minutes"],
            unknown_setting=call.data.get("unknown_setting", False),
        )
        _LOGGER.info("Mower settings written to %s", coordinator.address)
        return _service_response(call, result)

    async def _handle_set_work_times(call: ServiceCall) -> ServiceResponse | None:
        coordinator = _resolve_coordinator(hass, call)
        result = await coordinator.async_set_work_times(
            starts=[(s[0], s[1]) for s in call.data["starts"]],
            durations=[(d[0], d[1]) for d in call.data["durations"]],
        )
        _LOGGER.info("Work time schedule written to %s", coordinator.address)
        return _service_response(call, result)

    async def _handle_get_multi_area(call: ServiceCall) -> ServiceResponse | None:
        coordinator = _resolve_coordinator(hass, call)
        result = await coordinator.async_get_multi_area()
        _LOGGER.info(
            "Multi-area settings from %s: %s",
            coordinator.address, result.get("multi_area"),
        )
        return _service_response(call, result)

    async def _handle_get_mower_settings(call: ServiceCall) -> ServiceResponse | None:
        coordinator = _resolve_coordinator(hass, call)
        result = await coordinator.async_get_mower_settings()
        _LOGGER.info(
            "Mower settings from %s: %s",
            coordinator.address, result.get("mower_settings"),
        )
        return _service_response(call, result)

    async def _handle_get_work_times(call: ServiceCall) -> ServiceResponse | None:
        coordinator = _resolve_coordinator(hass, call)
        result = await coordinator.async_get_work_times()
        _LOGGER.info(
            "Work time schedule from %s: starts=%s durations=%s",
            coordinator.address,
            result.get("work_time_starts"),
            result.get("work_time_durations"),
        )
        return _service_response(call, result)

    services = (
        (
            SERVICE_SEND_RAW_JSON,
            _handle_send_raw_json,
            SERVICE_SEND_RAW_JSON_SCHEMA,
        ),
        (SERVICE_CHANGE_PIN, _handle_change_pin, SERVICE_CHANGE_PIN_SCHEMA),
        (
            SERVICE_SET_MULTI_AREA,
            _handle_set_multi_area,
            SERVICE_SET_MULTI_AREA_SCHEMA,
        ),
        (
            SERVICE_SET_MOWER_SETTINGS,
            _handle_set_mower_settings,
            SERVICE_SET_MOWER_SETTINGS_SCHEMA,
        ),
        (SERVICE_SET_WORK_TIMES, _handle_set_work_times, SERVICE_SET_WORK_TIMES_SCHEMA),
        (SERVICE_GET_MULTI_AREA, _handle_get_multi_area, SERVICE_GET_SETTINGS_SCHEMA),
        (
            SERVICE_GET_MOWER_SETTINGS,
            _handle_get_mower_settings,
            SERVICE_GET_SETTINGS_SCHEMA,
        ),
        (SERVICE_GET_WORK_TIMES, _handle_get_work_times, SERVICE_GET_SETTINGS_SCHEMA),
    )

    if all(hass.services.has_service(DOMAIN, service) for service, _, _ in services):
        return

    for service, handler, schema in services:
        if hass.services.has_service(DOMAIN, service):
            continue
        _async_register_service(
            hass,
            service,
            handler,
            schema,
            SupportsResponse.OPTIONAL,
        )
