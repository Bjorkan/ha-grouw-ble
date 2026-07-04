"""Test support for local and Home Assistant test environments."""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from datetime import UTC
from enum import Enum
import sys
import types
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
local_pygrouw = Path(__file__).resolve().parents[2] / "pyGrouw" / "src"
if local_pygrouw.exists():
    sys.path.insert(0, str(local_pygrouw))


def _install_module(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    sys.modules.setdefault(name, module)
    return sys.modules[name]


def _install_lightweight_stubs() -> None:
    """Install small stubs when Home Assistant is not available locally."""
    voluptuous = _install_module("voluptuous")

    class _Schema:
        def __init__(self, schema: Any) -> None:
            self.schema = schema

        def __call__(self, data: Any) -> Any:
            return data

    voluptuous.Schema = _Schema
    voluptuous.Required = lambda key, *args, **kwargs: key
    voluptuous.Optional = lambda key, *args, **kwargs: key

    class _Validator:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

        def __call__(self, value: Any) -> Any:
            return value

    voluptuous.All = _Validator
    voluptuous.Coerce = _Validator
    voluptuous.Range = _Validator
    voluptuous.Length = _Validator

    homeassistant = _install_module("homeassistant")
    homeassistant.__version__ = "test"

    components = _install_module("homeassistant.components")
    bluetooth = _install_module("homeassistant.components.bluetooth")
    components.bluetooth = bluetooth
    bluetooth.async_ble_device_from_address = lambda *args, **kwargs: None

    lawn_mower = _install_module("homeassistant.components.lawn_mower")
    components.lawn_mower = lawn_mower

    class _LawnMowerActivity:
        MOWING = "mowing"
        PAUSED = "paused"
        DOCKED = "docked"
        RETURNING = "returning"

    class _LawnMowerEntityFeature:
        START_MOWING = 1
        PAUSE = 2
        DOCK = 4

    class _LawnMowerEntity:
        """Minimal LawnMowerEntity stub."""

    lawn_mower.LawnMowerActivity = _LawnMowerActivity
    lawn_mower.LawnMowerEntity = _LawnMowerEntity
    lawn_mower.LawnMowerEntityFeature = _LawnMowerEntityFeature

    sensor = _install_module("homeassistant.components.sensor")
    components.sensor = sensor

    class SensorDeviceClass:
        BATTERY = "battery"
        DURATION = "duration"

    class SensorEntity:
        """Minimal SensorEntity stub."""

    @dataclass(frozen=True, kw_only=True)
    class SensorEntityDescription:
        key: str
        translation_key: str | None = None
        device_class: Any = None
        entity_category: Any = None
        native_unit_of_measurement: str | None = None

    sensor.SensorDeviceClass = SensorDeviceClass
    sensor.SensorEntity = SensorEntity
    sensor.SensorEntityDescription = SensorEntityDescription

    binary_sensor = _install_module("homeassistant.components.binary_sensor")
    components.binary_sensor = binary_sensor

    class BinarySensorEntity:
        """Minimal BinarySensorEntity stub."""

    @dataclass(frozen=True, kw_only=True)
    class BinarySensorEntityDescription:
        key: str
        translation_key: str | None = None
        entity_category: Any = None
        icon: str | None = None

    binary_sensor.BinarySensorEntity = BinarySensorEntity
    binary_sensor.BinarySensorEntityDescription = BinarySensorEntityDescription

    config_entries = _install_module("homeassistant.config_entries")

    class ConfigEntry:
        """Minimal config entry stub."""

    config_entries.ConfigEntry = ConfigEntry

    const = _install_module("homeassistant.const")
    const.CONF_NAME = "name"
    const.EntityCategory = types.SimpleNamespace(DIAGNOSTIC="diagnostic")
    const.PERCENTAGE = "%"

    class Platform:
        LAWN_MOWER = "lawn_mower"
        SENSOR = "sensor"
        BINARY_SENSOR = "binary_sensor"

    const.Platform = Platform

    core = _install_module("homeassistant.core")

    class HomeAssistant:
        """Minimal hass stub."""

    class ServiceCall:
        """Minimal service call stub."""

    class SupportsResponse(Enum):
        OPTIONAL = "optional"
        ONLY = "only"

    core.HomeAssistant = HomeAssistant
    core.ServiceCall = ServiceCall
    core.ServiceResponse = dict[str, Any]
    core.SupportsResponse = SupportsResponse

    exceptions = _install_module("homeassistant.exceptions")

    class ConfigEntryNotReady(Exception):
        """Config entry setup should be retried."""

    class ConfigEntryAuthFailed(Exception):
        """Config entry needs reauthentication."""

    class HomeAssistantError(Exception):
        """Base Home Assistant user-facing error."""

    class ServiceValidationError(HomeAssistantError):
        """Service call validation error."""

    exceptions.ConfigEntryNotReady = ConfigEntryNotReady
    exceptions.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    exceptions.HomeAssistantError = HomeAssistantError
    exceptions.ServiceValidationError = ServiceValidationError

    helpers = _install_module("homeassistant.helpers")
    config_validation = _install_module("homeassistant.helpers.config_validation")
    helpers.config_validation = config_validation
    config_validation.string = str
    config_validation.boolean = lambda v: v
    config_validation.ensure_list = lambda v: v if isinstance(v, list) else [v]
    import re as _re
    config_validation.matches_regex = lambda regex: (
        (lambda v: v if _re.compile(regex).search(v) else (_ for _ in ()).throw(ValueError(f"does not match {regex}")))
    )

    entity_platform = _install_module("homeassistant.helpers.entity_platform")
    helpers.entity_platform = entity_platform

    def _add_entities_callback(*args: Any, **kwargs: Any) -> Any:
        return None

    entity_platform.AddEntitiesCallback = _add_entities_callback

    update_coordinator = _install_module("homeassistant.helpers.update_coordinator")

    class UpdateFailed(Exception):
        """Coordinator update failed."""

    class DataUpdateCoordinator:
        """Small subset of Home Assistant's DataUpdateCoordinator."""

        def __class_getitem__(cls, item: Any) -> type:
            return cls

        def __init__(
            self,
            hass: HomeAssistant,
            logger: Any,
            *,
            name: str,
            update_interval: Any = None,
        ) -> None:
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.data = None
            self.last_update_success = True

        async def async_config_entry_first_refresh(self) -> None:
            self.data = await self._async_update_data()

        def async_set_updated_data(self, data: Any) -> None:
            self.data = data
            self.last_update_success = True

        async def async_request_refresh(self) -> None:
            try:
                self.data = await self._async_update_data()
                self.last_update_success = True
            except Exception:
                self.last_update_success = False
                raise

    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.UpdateFailed = UpdateFailed

    device_registry = _install_module("homeassistant.helpers.device_registry")
    helpers.device_registry = device_registry
    device_registry.CONNECTION_BLUETOOTH = "bluetooth"

    entity = _install_module("homeassistant.helpers.entity")
    helpers.entity = entity

    class DeviceInfo(dict):
        """Minimal DeviceInfo stub."""

    entity.DeviceInfo = DeviceInfo

    class CoordinatorEntity:
        """Minimal CoordinatorEntity stub."""

        def __class_getitem__(cls, item: Any) -> type:
            return cls

        def __init__(self, coordinator: Any) -> None:
            self.coordinator = coordinator
            self.entity_description: Any = None
            self._attr_has_entity_name = True
            self._attr_name: str | None = None
            self._attr_unique_id: str | None = None

        @property
        def available(self) -> bool:
            return True

        @property
        def device_info(self) -> DeviceInfo:
            return DeviceInfo()

    update_coordinator.CoordinatorEntity = CoordinatorEntity

    bleak = _install_module("bleak")
    bleak.__path__ = []
    bleak_backends = _install_module("bleak.backends")
    bleak_backends.__path__ = []
    bleak_device = _install_module("bleak.backends.device")

    class BleakClient:
        """Minimal BleakClient stub."""

    class BleakError(Exception):
        """Minimal BleakError stub."""

    class BleakScanner:
        """Minimal BleakScanner stub."""

        @classmethod
        async def discover(cls, *args: Any, **kwargs: Any) -> list[Any]:
            return []

    class BLEDevice:
        """Minimal BLEDevice stub."""

    bleak.BleakClient = BleakClient
    bleak.BleakError = BleakError
    bleak.BleakScanner = BleakScanner
    bleak_backends.device = bleak_device
    bleak_device.BLEDevice = BLEDevice

    bleak_retry_connector = _install_module("bleak_retry_connector")

    async def establish_connection(*args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    bleak_retry_connector.establish_connection = establish_connection


if importlib.util.find_spec("homeassistant") is None:
    _install_lightweight_stubs()


if importlib.util.find_spec("pytest_homeassistant_custom_component") is not None:
    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import MockModule, mock_integration

    @pytest.fixture(autouse=True)
    def reset_default_timezone() -> None:
        """Keep Home Assistant's global timezone clean between tests."""
        dt_util.DEFAULT_TIME_ZONE = UTC
        yield
        dt_util.DEFAULT_TIME_ZONE = UTC

    @pytest.fixture
    def expected_lingering_timers() -> bool:
        """Allow Home Assistant's test harness cleanup timers."""
        return True

    @pytest.fixture
    def mock_bluetooth_adapters(
        hass: Any, enable_custom_integrations: Any
    ) -> None:
        """Mock HA's Bluetooth adapter dependency without opening real sockets."""

        async def _async_setup(*args: Any, **kwargs: Any) -> bool:
            return True

        mock_integration(
            hass,
            MockModule("bluetooth_adapters", async_setup=_async_setup),
        )
