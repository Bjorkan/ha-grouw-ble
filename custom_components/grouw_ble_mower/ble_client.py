"""BLE client for Grouw/robotic-mower connect mowers."""
from __future__ import annotations

import asyncio
from collections.abc import Iterable
import logging
from typing import Any

from bleak import BleakClient, BleakError
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .ble_protocol import encode_json_frame, extract_payloads, parse_payload
from .const import (
    CMD_REQUEST_ALL_INFO,
    CMD_SET_MODE,
    DEFAULT_BLE_TIMEOUT,
    DEFAULT_CHUNK_DELAY,
    READ_CHARACTERISTIC_UUID,
    RESP_ACK,
    RESP_ALL_INFO,
    RESP_HOME_RESULT,
    RESP_MACHINE_STATUS,
    RESP_STOP_RESULT,
    RESP_WORK_RESULT,
    RESP_WORK_STATUS,
    WRITE_CHARACTERISTIC_UUID,
)

_LOGGER = logging.getLogger(__name__)


class GrouwBleError(Exception):
    """Base BLE communication error."""


class GrouwBleDeviceNotFound(GrouwBleError):
    """Raised when Home Assistant has no connectable BLE device for the address."""


class GrouwBleTimeout(GrouwBleError):
    """Raised when a BLE request times out."""


class GrouwBleMowerClient:
    """Small stateless BLE client.

    It obtains the BLEDevice from Home Assistant's Bluetooth manager on every
    request. That keeps it compatible with normal Bluetooth adapters and
    connectable Bluetooth proxies.
    """

    def __init__(self, hass: HomeAssistant, address: str, name: str) -> None:
        self.hass = hass
        self.address = address.upper()
        self.name = name

    async def async_request_json(
        self,
        payload: dict[str, Any],
        *,
        expect_cmds: Iterable[int] | None = None,
        timeout: float = DEFAULT_BLE_TIMEOUT,
    ) -> dict[str, Any]:
        """Send a framed JSON payload and wait for a matching JSON response."""
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            raise GrouwBleDeviceNotFound(
                f"No connectable Bluetooth device found for {self.address}"
            )

        expected = set(expect_cmds or [])
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        buffer = bytearray()
        loop = asyncio.get_running_loop()

        def _notification_handler(_sender: int | str, data: bytearray) -> None:
            buffer.extend(bytes(data))
            for raw_payload in extract_payloads(buffer):
                message = parse_payload(raw_payload)
                if message is None:
                    continue
                loop.call_soon_threadsafe(queue.put_nowait, message)

        client: BleakClient | None = None
        try:
            client = await establish_connection(
                BleakClient,
                ble_device,
                self.name,
                max_attempts=3,
                timeout=timeout,
            )
            await client.start_notify(READ_CHARACTERISTIC_UUID, _notification_handler)

            for packet in encode_json_frame(payload):
                await client.write_gatt_char(
                    WRITE_CHARACTERISTIC_UUID, packet, response=False
                )
                await asyncio.sleep(DEFAULT_CHUNK_DELAY)

            while True:
                message = await asyncio.wait_for(queue.get(), timeout=timeout)
                cmd = message.get("cmd")
                if not expected or cmd in expected:
                    return message
                _LOGGER.debug("Ignoring BLE response with unexpected cmd %s: %s", cmd, message)
        except asyncio.TimeoutError as err:
            raise GrouwBleTimeout(f"Timeout waiting for {self.address}") from err
        except BleakError as err:
            raise GrouwBleError(str(err)) from err
        finally:
            if client is not None:
                try:
                    await client.stop_notify(READ_CHARACTERISTIC_UUID)
                except Exception:  # noqa: BLE001 - disconnect cleanup must be best effort
                    pass
                try:
                    await client.disconnect()
                except Exception:  # noqa: BLE001
                    pass

    async def async_get_all_info(self) -> dict[str, Any]:
        """Request the Android app's all-info packet."""
        return await self.async_request_json(
            {"cmd": CMD_REQUEST_ALL_INFO},
            expect_cmds={RESP_ALL_INFO, RESP_WORK_STATUS, RESP_MACHINE_STATUS},
        )

    async def async_set_mode(
        self, mode: int, point: int | None = None
    ) -> dict[str, Any]:
        """Send a work-mode command."""
        payload: dict[str, Any] = {"cmd": CMD_SET_MODE, "mode": int(mode)}
        if point is not None:
            payload["point"] = int(point)
        return await self.async_request_json(
            payload,
            expect_cmds={
                RESP_ACK,
                RESP_STOP_RESULT,
                RESP_WORK_RESULT,
                RESP_HOME_RESULT,
                RESP_WORK_STATUS,
                RESP_MACHINE_STATUS,
                RESP_ALL_INFO,
            },
        )

    async def async_send_raw_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a raw JSON payload and return the first JSON response."""
        return await self.async_request_json(payload)
