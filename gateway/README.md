# Raspberry Pi RS485 gateway

This folder is a self-contained companion project for
[Dantherm HCH PassiveLink](../README.md). It turns a Raspberry Pi with a
USB-RS485 adapter into a receive-only RS485-to-Ethernet bridge.

The bridge mirrors observed `19200 8E1` bytes to raw TCP port `4196`. It does
not generate Modbus requests or write to the serial port. The existing Dantherm
controller remains in charge.

## Included files

| File | Purpose |
| --- | --- |
| `passivelink_gateway.py` | Receive-only serial-to-TCP bridge |
| `dantherm-passivelink.service` | Automatically starts and restarts the bridge |
| `gateway.example.env` | Adapter path, bind address and TCP port |
| `install.sh` | Idempotent installer for Raspberry Pi OS Lite |
| `onewire_temperature_server.py` | Optional DS18B20 temperature service |
| `dantherm-passivelink-onewire.service` | Optional temperature service |
| `onewire.example.json` | Optional flow/return probe assignment |

## Quick start

Install Raspberry Pi OS Lite (32-bit), enable SSH and connect the Pi by
Ethernet. Clone this repository on the Pi, then run:

```bash
git clone https://github.com/MRDonnii/dantherm-hch-passivelink.git
cd dantherm-hch-passivelink
ls -l /dev/serial/by-id/
sudo gateway/install.sh --device /dev/serial/by-id/YOUR_ADAPTER
```

The installer creates an unprivileged `passivelink` account, a Python virtual
environment, `/etc/dantherm-passivelink/gateway.env`, and an enabled systemd
service. Verify it with:

```bash
systemctl status dantherm-passivelink.service --no-pager
journalctl -u dantherm-passivelink.service -n 50 --no-pager
ss -lntp | grep 4196
```

Then add the Home Assistant integration in **RS485 over TCP** mode and enter
the Raspberry Pi address and port `4196`.

For wiring, fixed IP configuration, watchdog, firewall, troubleshooting and
the optional water-preheater probes, follow the complete guides:

- [Dansk trin-for-trin-guide](../docs/raspberry-pi-gateway.da.md)
- [English step-by-step guide](../docs/raspberry-pi-gateway.en.md)

## Safety

This unofficial project is not affiliated with or supported by Dantherm
Group. Power down equipment before changing wiring. Keep the existing
controller connection intact, do not add an unnecessary bus terminator, and
never expose the raw TCP port to the internet.
