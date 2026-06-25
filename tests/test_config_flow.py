"""Home Assistant config flow tests."""
from __future__ import annotations

from unittest.mock import patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.grouw_ble_mower.const import DOMAIN


async def test_user_form(hass: HomeAssistant, mock_bluetooth_adapters: None) -> None:
    """Test that the config flow user form can be shown."""
    with patch(
        "homeassistant.components.bluetooth.async_discovered_service_info",
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
