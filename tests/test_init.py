"""Home Assistant setup/unload tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grouw_ble_mower import async_setup_entry
from custom_components.grouw_ble_mower.const import CONF_ADDRESS, CONF_PIN, DOMAIN


async def test_setup_unload_entry(
    hass: HomeAssistant, mock_bluetooth_adapters: None
) -> None:
    """Test that the integration can be set up and unloaded."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test mower",
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "Test mower",
            CONF_PIN: "1234",
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    with patch.object(
        hass.config_entries,
        "async_forward_entry_setups",
        AsyncMock(return_value=True),
    ), patch.object(
        hass.config_entries,
        "async_unload_platforms",
        AsyncMock(return_value=True),
    ), patch(
        "custom_components.grouw_ble_mower.coordinator.GrouwMowerCoordinator.async_config_entry_first_refresh",
        AsyncMock(),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.LOADED

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.NOT_LOADED

    await hass.async_stop()
    await hass.async_block_till_done()


async def test_setup_entry_without_pin_requests_reauth(hass: HomeAssistant) -> None:
    """Old config entries without a PIN should ask Home Assistant for reauth."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test mower",
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "Test mower",
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )

    with pytest.raises(ConfigEntryAuthFailed, match="4-digit mower PIN"):
        await async_setup_entry(hass, entry)

    await hass.async_stop()
    await hass.async_block_till_done()
