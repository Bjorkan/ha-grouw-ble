"""BLE client for Grouw/Daye mower devices."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from bleak import BleakClient, BleakError
from bleak_retry_connector import establish_connection

from homeassistant.core import HomeAssistant

from .ble_protocol import (
    DAYE_RESPONSE_PIN_OR_AUTH,
    DAYE_RESPONSE_STATUS,
    encode_daye_command,
    encode_daye_session_start,
    encode_raw_payload,
    parse_daye_payload,
    redact_daye_message,
)
from .const import (
    DEFAULT_BLE_TIMEOUT,
    DEFAULT_CHUNK_DELAY,
    READ_CHARACTERISTIC_UUID,
    WRITE_CHARACTERISTIC_UUID,
)

_LOGGER = logging.getLogger(__name__)


class GrouwBleError(Exception):
    """Base BLE communication error."""


class GrouwBleDeviceNotFound(GrouwBleError):
    """Raised when Home Assistant has no connectable BLE device for the address."""


class GrouwBleTimeout(GrouwBleError):
    """Raised when a BLE request times out."""


class GrouwBleConnectionError(GrouwBleError):
    """Raised when BLE connection fails."""


class GrouwBleGattError(GrouwBleError):
    """Raised on GATT write/notify failure."""


class GrouwBleAuthenticationError(GrouwBleError):
    """Raised when mower PIN authentication fails."""


def _drain_queue(queue: asyncio.Queue) -> None:
    """Discard all items currently in the queue."""
    while not queue.empty():
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            break


class GrouwBleMowerClient:
    """Small stateless BLE client.

    It obtains the BLEDevice from Home Assistant's Bluetooth manager on every
    request. That keeps it compatible with normal Bluetooth adapters and
    connectable Bluetooth proxies.
    """

    def __init__(
        self, hass: HomeAssistant, address: str, name: str, pin: str = ""
    ) -> None:
        self.hass = hass
        self.address = address.upper()
        self.name = name
        self.pin = pin.strip()
        self._tx_counter = 0

    async def _write_with_log(
        self,
        client: BleakClient,
        payload: bytes,
        label: str,
    ) -> None:
        """Write to GATT characteristic and log the result."""
        try:
            await client.write_gatt_char(
                WRITE_CHARACTERISTIC_UUID, payload, response=True
            )
            _LOGGER.debug(
                "[%s tx=%s] write %s ok payload=%s",
                self.address, self._tx_id, label, payload.hex()
            )
        except BleakError as err:
            _LOGGER.error(
                "[%s tx=%s] write %s failed: %s (errno=%s)",
                self.address, self._tx_id, label, err,
                getattr(err, "args", ("unknown",))
            )
            raise GrouwBleGattError(
                f"GATT write failed for {label} on {self.address}: {err}"
            ) from err

    async def _wait_for_response(
        self,
        queue: asyncio.Queue[dict[str, Any]],
        expected_cmd: int | None,
        timeout: float,
        phase: str,
    ) -> dict[str, Any]:
        """Wait for a parsed notification with the expected DYM command byte."""
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=timeout)
            except asyncio.TimeoutError as err:
                _LOGGER.error(
                    "[%s tx=%s] notification timeout in %s (expected_cmd=%s)",
                    self.address, self._tx_id, phase, expected_cmd
                )
                raise GrouwBleTimeout(
                    f"Timeout waiting for notification from {self.address}"
                ) from err

            cmd = message.get("cmd")
            if expected_cmd is None or cmd == expected_cmd:
                _LOGGER.debug(
                    "[%s tx=%s] selected %s response cmd=%s raw=%s",
                    self.address, self._tx_id, phase, cmd,
                    redact_daye_message(message).get("raw_hex", "?")
                )
                return message

            _LOGGER.debug(
                "[%s tx=%s] ignoring notification cmd=%s in %s (waiting for %s)",
                self.address, self._tx_id, cmd, phase, expected_cmd
            )

    def _verify_auth_response(self, message: dict[str, Any]) -> None:
        """Verify the configured PIN against the mower auth/PIN response."""
        if not self.pin:
            return

        mower_pin = message.get("mower_pin")
        if mower_pin is None:
            raise GrouwBleAuthenticationError(
                "Mower auth response did not include PIN data; cannot verify configured PIN"
            )

        if str(mower_pin) != self.pin:
            raise GrouwBleAuthenticationError(
                "Configured mower PIN does not match the mower auth response"
            )

        _LOGGER.debug(
            "[%s tx=%s] configured PIN verified against mower auth response",
            self.address, self._tx_id
        )

    async def async_request_daye(
        self,
        payload: bytes,
        follow_up_status: bool = False,
        authenticate: bool = True,
        expected_cmd: int | None = DAYE_RESPONSE_STATUS,
        timeout: float = DEFAULT_BLE_TIMEOUT,
        command_name: str = "raw",
    ) -> dict[str, Any]:
        """Send a Daye DYM payload and wait for the first parsed notification."""
        self._tx_counter += 1
        self._tx_id = self._tx_counter

        _LOGGER.debug(
            "[%s tx=%s] request starting command=%s follow_up=%s authenticate=%s",
            self.address, self._tx_id, command_name, follow_up_status, authenticate
        )

        from homeassistant.components import bluetooth

        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            _LOGGER.error(
                "[%s tx=%s] no connectable BLE device found",
                self.address, self._tx_id
            )
            raise GrouwBleDeviceNotFound(
                f"No connectable Bluetooth device found for {self.address}"
            )

        _LOGGER.debug(
            "[%s tx=%s] BLE device resolved", self.address, self._tx_id
        )

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _notification_handler(_sender: int | str, data: bytearray) -> None:
            message = parse_daye_payload(bytes(data))
            if message is not None:
                _LOGGER.debug(
                    "[%s tx=%s] notify raw=%s",
                    self.address, self._tx_id,
                    redact_daye_message(message).get("raw_hex", data.hex())
                )
                loop.call_soon_threadsafe(queue.put_nowait, message)

        client: BleakClient | None = None
        try:
            _LOGGER.debug(
                "[%s tx=%s] connecting (timeout=%s)",
                self.address, self._tx_id, timeout
            )
            try:
                client = await establish_connection(
                    BleakClient,
                    ble_device,
                    self.name,
                    max_attempts=3,
                    timeout=timeout,
                )
            except BleakError as err:
                _LOGGER.error(
                    "[%s tx=%s] connect failed: %s",
                    self.address, self._tx_id, err
                )
                raise GrouwBleConnectionError(
                    f"BLE connect failed for {self.address}: {err}"
                ) from err

            _LOGGER.debug(
                "[%s tx=%s] connected, starting notify",
                self.address, self._tx_id
            )
            try:
                await client.start_notify(
                    READ_CHARACTERISTIC_UUID, _notification_handler
                )
            except BleakError as err:
                _LOGGER.error(
                    "[%s tx=%s] start_notify failed: %s",
                    self.address, self._tx_id, err
                )
                raise GrouwBleGattError(
                    f"GATT start_notify failed on {self.address}: {err}"
                ) from err

            _LOGGER.debug(
                "[%s tx=%s] notify started", self.address, self._tx_id
            )

            if authenticate:
                await self._write_with_log(
                    client, encode_daye_session_start(), "session_start"
                )
                await asyncio.sleep(DEFAULT_CHUNK_DELAY)
                await self._write_with_log(
                    client, encode_daye_command("auth_query"), "auth_query"
                )
                auth_message = await self._wait_for_response(
                    queue,
                    DAYE_RESPONSE_PIN_OR_AUTH,
                    timeout,
                    "auth",
                )
                self._verify_auth_response(auth_message)

                _drain_queue(queue)
                _LOGGER.debug(
                    "[%s tx=%s] queue drained after auth",
                    self.address, self._tx_id
                )

            await self._write_with_log(client, payload, "command")
            if follow_up_status:
                await asyncio.sleep(DEFAULT_CHUNK_DELAY)
                await self._write_with_log(
                    client, encode_daye_command("status"), "follow_up_status"
                )

            return await self._wait_for_response(
                queue,
                expected_cmd,
                timeout,
                "command",
            )

        except (
            GrouwBleAuthenticationError,
            GrouwBleConnectionError,
            GrouwBleGattError,
            GrouwBleTimeout,
        ):
            raise
        except BleakError as err:
            _LOGGER.error(
                "[%s tx=%s] unexpected BleakError: %s",
                self.address, self._tx_id, err
            )
            raise GrouwBleError(
                f"Unexpected BLE error on {self.address}: {err}"
            ) from err
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
                _LOGGER.debug(
                    "[%s tx=%s] disconnected", self.address, self._tx_id
                )

    async def async_get_all_info(self) -> dict[str, Any]:
        """Request the Daye status packet captured from the official app."""
        return await self.async_request_daye(
            encode_daye_command("status"),
            command_name="status",
        )

    async def async_command(self, command: str) -> dict[str, Any]:
        """Send a Daye mower command and refresh status."""
        return await self.async_request_daye(
            encode_daye_command(command),
            follow_up_status=True,
            command_name=command,
        )

    async def async_send_raw_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a raw debug payload and return the first parsed notification."""
        try:
            raw_payload = encode_raw_payload(payload)
        except ValueError as err:
            raise GrouwBleError(str(err)) from err
        expected = payload.get("expect_cmd", DAYE_RESPONSE_STATUS)
        expected_cmd = None if expected is None else int(expected)
        authenticate = bool(payload.get("authenticate", True))
        return await self.async_request_daye(
            raw_payload,
            authenticate=authenticate,
            expected_cmd=expected_cmd,
            command_name=str(payload.get("command", "raw")),
        )
