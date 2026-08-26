# Dantherm HCH PassiveLink

![Dantherm HCH PassiveLink logo](assets/logo.png)

An unofficial, strictly read-only Home Assistant integration for a Dantherm HCH5 MK1 with HAC1. It decodes the existing internal Modbus RTU traffic without becoming a second bus master.

> **Unofficial community project:** This software was not developed, supplied, commissioned, approved, certified or supported by Dantherm Group. Dantherm Group is not affiliated with this project. “Dantherm” is used only to identify compatible equipment; all trademarks belong to their respective owners. For product service and safety questions, contact Dantherm or an authorised installer.

## Safety model

The integration supports a raw TCP stream or a USB-RS485 adapter connected directly to the Home Assistant host. Both modes **only receive bytes** and contain no Modbus request generator or serial write call. Configure the serial side as `19200 8E1`. For Ethernet adapters, disable polling, Modbus TCP conversion, MQTT and any heartbeat or registration data sent over the serial port.

For direct USB use, select **USB-RS485** during setup and enter a stable path such as `/dev/serial/by-id/...`. Home Assistant must have permission to access that device, and no other process may open the same serial port.

Do not use an M-Bus gateway. M-Bus is electrically incompatible with RS485.

## Why it is read-only

Our observations of the HCH5 MK1 + HAC1 installation show an existing controller acting as the Modbus RTU master. It continuously sends requests, and the ventilation unit replies as a slave. Those request/response frames already contain the operating values needed by Home Assistant, so this integration can decode them without polling the unit itself.

The installation is operated as a single-master Modbus RTU bus. A second device can technically transmit a valid command, and the unit may accept it temporarily. However, the existing master continues its normal control cycle and writes its own state again, so the external value is overwritten. Two independent transmitters on the same RS485 pair also have no arbitration: their frames can overlap, cause CRC and timeout errors, disturb the existing controller and potentially produce unintended behaviour.

Because writes would be unreliable, temporary and potentially disruptive, read-only operation is a deliberate design and safety choice rather than a missing feature:

- the gateway listens to both directions of the existing RS485 exchange;
- the gateway forwards the observed bytes as an unchanged raw TCP stream;
- the Home Assistant integration only receives and decodes that stream;
- neither the gateway nor the integration may poll, acknowledge or write to the bus.

A transparent RS485-to-Ethernet adapter is suitable when it can expose the observed serial bytes as a raw TCP stream without generating its own serial traffic. The integration never writes data to its TCP connection. Do not connect other software that sends data through the adapter.

### Adapter setup

Configure the adapter before adding the integration:

- serial interface: RS485;
- baud rate: `19200`;
- data format: `8E1` (8 data bits, even parity, 1 stop bit);
- network mode: transparent/raw TCP server;
- protocol conversion: disabled;
- active polling, MQTT and serial heartbeat/registration packets: disabled.

Connect the adapter passively to the same RS485 A/B pair and enter the adapter's own IP address and TCP listening port in Home Assistant. The address and port are chosen in the adapter configuration and are not fixed by this integration.

A detailed Danish explanation of the findings is available in [docs/findings.da.md](docs/findings.da.md).

## Entities

Temperatures, CO₂, after-heater setpoint, both fan speeds and control percentages, operating mode, ventilation level, bypass, fireplace/standby/night states, HAC1 connectivity and raw diagnostic values. Unverified raw values are disabled by default and are deliberately not presented with misleading units.

Names and setup text are included in Danish and English and follow the selected Home Assistant language.

## Installation with HACS

1. Use `https://github.com/MRDonnii/dantherm-hch-passivelink` as a HACS custom repository.
2. In HACS, add that URL as a custom repository of type **Integration**.
3. Install **Dantherm HCH PassiveLink** and restart Home Assistant.
4. Add the integration under **Settings → Devices & services**.
5. Enter the IP address and raw TCP listening port configured on the RS485-to-Ethernet adapter.

If the adapter address changes later, reconfigure the integration with its new host and port.

## Compatibility

The decoder is based on controlled observations from one HCH5 MK1 + HAC1 installation. It is not intended for HCH5 MKII or newer units that provide official Modbus TCP.

Dantherm Group has not supplied this integration and provides no support or warranty for it.
