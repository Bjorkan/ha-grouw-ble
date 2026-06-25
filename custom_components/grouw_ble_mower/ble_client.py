"""BLE client for Grouw/Daye mower devices."""
from __future__ import annotations

import asyncio
from typing import Any

from bleak import BleakClient, BleakError
from bleak_retry_connector import establish_connection

from homeassistant.core import HomeAssistant

from .ble_protocol import encode_daye_command, encode_raw_payload, parse_daye_payload
from .const import (
    DEFAULT_BLE_TIMEOUT,
    DEFAULT_CHUNK_DELAY,
    READ_CHARACTERISTIC_UUID,
    WRITE_CHARACTERISTIC_UUID,
)


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

    async def async_request_daye(
        self,
        payload: bytes,
        follow_up_status: bool = False,
        timeout: float = DEFAULT_BLE_TIMEOUT,
    ) -> dict[str, Any]:
        """Send a Daye DYM payload and wait for the first parsed notification."""
        from homeassistant.components import bluetooth

        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            raise GrouwBleDeviceNotFound(
                f"No connectable Bluetooth device found for {self.address}"
            )

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _notification_handler(_sender: int | str, data: bytearray) -> None:
            message = parse_daye_payload(bytes(data))
            if message is not None:
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

            await client.write_gatt_char(
                WRITE_CHARACTERISTIC_UUID, payload, response=True
            )
            if follow_up_status:
                await asyncio.sleep(DEFAULT_CHUNK_DELAY)
                await client.write_gatt_char(
                    WRITE_CHARACTERISTIC_UUID,
                    encode_daye_command("status"),
                    response=True,
                )

            while True:
                message = await asyncio.wait_for(queue.get(), timeout=timeout)
                return message
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
        """Request the Daye status packet captured from the official app."""
        return await self.async_request_daye(encode_daye_command("status"))

    async def async_command(self, command: str) -> dict[str, Any]:
        """Send a Daye mower command and refresh status."""
        return await self.async_request_daye(
            encode_daye_command(command),
            follow_up_status=True,
        )

    async def async_send_raw_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a raw debug payload and return the first parsed notification."""
        try:
            raw_payload = encode_raw_payload(payload)
        except ValueError as err:
            raise GrouwBleError(str(err)) from err
        return await self.async_request_daye(raw_payload)
