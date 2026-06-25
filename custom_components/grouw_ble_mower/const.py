"""Constants for the Grouw/Daye BLE Mower integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "grouw_ble_mower"

READ_CHARACTERISTIC_UUID = ""
WRITE_CHARACTERISTIC_UUID = ""

DEFAULT_NAME = "Grouw / Daye BLE Mower"
APP_PACKAGE = "com.dayepower.dayeappleaf"
APP_NAME = "Daye Power robotic mower app"
SUPPORTED_LOCAL_NAME_PREFIXES = ("RobotMower_DYM", "Robot_Mower")
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=60)
DEFAULT_BLE_TIMEOUT = 15.0
DEFAULT_CHUNK_DELAY = 0.03

CONF_ADDRESS = "address"

SERVICE_SEND_RAW_JSON = "send_raw_json"
