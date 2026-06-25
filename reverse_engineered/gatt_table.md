# GATT Table

Confirmed from an iPhone BLE scan near the mower:

```text
Device name: Robot Mower_DYM

Service 180A
  Characteristic 2A29 Manufacturer Name String
  Characteristic 2A24 Model Number String
  Characteristic 2A25 Serial Number String
  Characteristic 2A27 Hardware Revision String
  Characteristic 2A26 Firmware Revision String
  Characteristic 2A28 Software Revision String
  Characteristic 2A23 System ID
  Characteristic 2A2A IEEE Regulatory Certification

Service 49535343-5D82-6099-9348-7AAC4D5FBC51
  Characteristic 49535343-026E-3A9B-954C-97DAEF17E26E

Service 49535343-C9D0-CC83-A44A-6FE238D06D33
  Characteristic 49535343-ACA3-481C-91EC-D85E28A60318

Service 49535343-FE7D-4AE5-8FA9-9FAFD205E455
  Characteristic 49535343-1E4D-4BD9-BA61-23C647249616
  Characteristic 49535343-8841-43F4-A8D4-ECBE34729BB3
  Characteristic 49535343-4C8A-39B3-2F49-511CFF073B7E
```

This confirms that `49535343-FE7D-4AE5-8FA9-9FAFD205E455` is a Daye/Grouw
mower GATT service, and that `49535343-1E4D-4BD9-BA61-23C647249616` is a
characteristic under that service (used for both write and notify).

## HCI-Confirmed Details

The Daye app's ATT discovery confirmed the primary control characteristic:

```text
Service 49535343-FE7D-4AE5-8FA9-9FAFD205E455, handles 0x0017-0x0020
  Declaration handle 0x0018
  Value handle       0x0019
  UUID               49535343-1E4D-4BD9-BA61-23C647249616
  Properties         0x1c: write without response, write, notify
  CCCD handle        0x001a
```

The Daye app enables notifications by writing `0100` to handle `0x001a`, then
uses ATT Write Request, not Write Command, to write payloads to handle `0x0019`.
Notifications arrive on the same handle.
