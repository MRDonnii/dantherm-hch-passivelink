# HCH PassiveLink

![HCH PassiveLink logo](assets/logo.png)

An unofficial, strictly read-only Home Assistant integration for a Dantherm HCH5 MK1 with HAC1. It decodes the existing internal Modbus RTU traffic without becoming a second bus master.

## Safety model

The integration opens a raw TCP socket and **only receives bytes**. It contains no socket write call and no Modbus request generator. Use it with:

- the included receive-only Lenovo USB-RS485 gateway (`10.0.0.11:4196`), or
- a transparent RS485-to-Ethernet adapter configured for raw TCP, `19200 8E1`, with polling, Modbus TCP conversion, MQTT and serial heartbeat disabled.

Do not use an M-Bus gateway. M-Bus is electrically incompatible with RS485.

## Entities

Temperatures, CO₂, after-heater setpoint, both fan speeds and control percentages, operating mode, ventilation level, bypass, fireplace/standby/night states, HAC1 connectivity and raw diagnostic values. Unverified raw values are disabled by default and are deliberately not presented with misleading units.

Names and setup text are included in Danish and English and follow the selected Home Assistant language.

## Installation with HACS

1. Publish this folder as `https://github.com/donnii/hch-passivelink`.
2. In HACS, add that URL as a custom repository of type **Integration**.
3. Install **HCH PassiveLink** and restart Home Assistant.
4. Add the integration under **Settings → Devices & services**.
5. Enter `10.0.0.11` and port `4196`.

Later, replace only the host and port with those of a transparent RS485-to-Ethernet adapter. Stable entity unique IDs preserve dashboards and history.

## Compatibility

The decoder is based on controlled observations from one HCH5 MK1 + HAC1 installation. It is not intended for HCH5 MKII or newer units that provide official Modbus TCP.

This project is not affiliated with or endorsed by Dantherm Group.

