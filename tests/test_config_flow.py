"""Home Assistant config flow tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.grouw_ble_mower.config_flow import (
    _has_supported_service_uuid,
    _is_supported_bluetooth_name,
    _is_valid_address,
    _is_valid_pin,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grouw_ble_mower.const import (
    CONF_ADDRESS,
    CONF_PIN,
    DAYE_PRIMARY_SERVICE_UUID,
    DOMAIN,
)


def test_supported_bluetooth_names_include_daye_app_device_name() -> None:
    """The Daye APK contains RobotMower_DYM and Robot_Mower name strings."""
    assert _is_supported_bluetooth_name("Robot Mower_DYM")
    assert _is_supported_bluetooth_name("Robot Mower_DYM-1234")
    assert _is_supported_bluetooth_name("RobotMower_DYM")
    assert _is_supported_bluetooth_name("RobotMower_DYM-1234")
    assert _is_supported_bluetooth_name("Robot_Mower")
    assert _is_supported_bluetooth_name("Robot_Mower-1234")
    assert not _is_supported_bluetooth_name("OtherDevice")


def test_supported_service_uuid_includes_confirmed_hardware_gatt_service() -> None:
    """The iPhone hardware scan confirmed the Daye primary GATT service."""
    assert _has_supported_service_uuid([DAYE_PRIMARY_SERVICE_UUID.upper()])
    assert not _has_supported_service_uuid(["0000180a-0000-1000-8000-00805f9b34fb"])


def test_manual_address_validation_rejects_blank_values() -> None:
    """Manual setup should not create config entries without a BLE address."""
    assert _is_valid_address("AA:BB:CC:DD:EE:FF")
    assert not _is_valid_address("")
    assert not _is_valid_address("   ")


def test_pin_validation_matches_daye_four_digit_pin_shape() -> None:
    """The config flow requires exactly four ASCII decimal digits."""
    assert not _is_valid_pin("")
    assert _is_valid_pin("1234")
    assert not _is_valid_pin("123")
    assert not _is_valid_pin("12345")
    assert not _is_valid_pin("abcd")
    assert not _is_valid_pin("１２３４")


async def test_user_form(hass: HomeAssistant, mock_bluetooth_adapters: None) -> None:
    """Test that the config flow user form can be shown."""
    with patch.object(
        bluetooth,
        "async_discovered_service_info",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    await hass.async_stop()
    await hass.async_block_till_done()


async def test_reauth_updates_existing_pin(
    hass: HomeAssistant, mock_bluetooth_adapters: None
) -> None:
    """Reauth should update the existing config entry PIN."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test mower",
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "Test mower",
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    with patch.object(
        hass.config_entries,
        "async_reload",
        AsyncMock(return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
                "unique_id": entry.unique_id,
            },
            data=entry.data,
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PIN: "4321"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PIN] == "4321"

    await hass.async_stop()
    await hass.async_block_till_done()
