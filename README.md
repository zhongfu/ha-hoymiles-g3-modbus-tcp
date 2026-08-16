# Home Assistant integration for Hoymiles G3 Modbus TCP

*AI slop disclaimer: this thing was written by deepseek-v4-flash-0731 with input from me.*

Home Assistant integration for the **Hoymiles G3 series** hybrid inverters (e.g. HIT-G3).
It reads inverter Modbus registers over Modbus/TCP and shows its live measurements in Home Assistant.

The integration is read-only; it doesn't write to the inverter (at least for now).

## Supported hardware

- Inverters: Hoymiles HIT-xxL-G3, possibly other G3-series hybrid inverters (e.g. HIS-xxL-G3)
- DTS: DTS-WL-G3, possibly other DTSes **with an Ethernet port**

Note: on the DTS-WL-G3, Modbus/TCP on port 502 is only exposed through Ethernet and requires
firmware v03.00.13+. **WiFi will not work.**

## Install

Before proceeding, make sure you connect your DTS via Ethernet first, and get your DTS's Ethernet IP.

Consider isolating the Ethernet interface on a separate VLAN for security (there's no auth on the
endpoint, so **anyone on the same network may be able to change settings**). You'll still need DHCP
on that VLAN though.

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zhongfu&repository=ha-hoymiles-g3-modbus-tcp&category=integration)

Add this repository as a custom repository (HACS → ⋯ → Custom repositories →
`https://github.com/zhongfu/ha-hoymiles-g3-modbus-tcp`, category Integration),
install "Hoymiles G3 Modbus TCP" from HACS, then add it via Settings → Devices &
Services → Add Integration.

### Manual

1. Copy the `custom_components/hoymiles_g3_modbus_tcp` folder into your Home
   Assistant `config/custom_components/` folder.
2. Restart Home Assistant.
3. Add the integration via Settings → Devices & Services → Add Integration →
   "Hoymiles G3 Modbus TCP" and enter your Ethernet stick's IP address. Defaults:
   port `502`, unit `1`, and a poll interval of 10 seconds. You can change any of
   these later under **Settings → Devices & Services → ⋯ → Options**.

## What you get

Your inverter's data is organised into **four devices**:

| Device | Shows |
|--------|-------|
| **Battery** | battery state and measurements: charge level, voltage, current, power, cell temperatures, etc. |
| **Solar** | PV per-string and total power, voltage and current |
| **Grid Meter** | the external grid and PV meter readings (per-phase and total voltage, current, power, power factor, frequency, link status) |
| **Inverter** | everything else: mains/AC/backup/generator/energy, status and diagnostics |

Read-only settings (export limits, SOC range, EMS/SOC limits, EPS/PV island mode,
battery type, topology, …) show up as **Configuration** controls on the **Inverter** device.
They're read-only for now, so edits won't take effect.

All known registers are exposed, though some diagnostics entities are disabled by default
(and can be enabled).

Energy readings are shown as daily and lifetime totals, but you can use
[Utility Meter helpers](https://www.home-assistant.io/integrations/utility_meter/)
if you want e.g. monthly totals.

## Polling

Fast-moving measurements (powers, currents, voltages, frequency, energy) refresh every
`poll_interval` (default 10 seconds). Full polls run every `full_poll_interval`
(default 60 seconds) and reads everything else, e.g. temperatures, battery SoH, settings.

I've tested `poll_interval`s as low as 5s (but it can probably go lower; each poll takes
~2-3s for me).

Polls are done with large block register reads by the [underlying library](https://github.com/zhongfu/hoymiles-g3-modbus-tcp),
so it's possible that other "slow poll" registers get polled during the fast poll if they happen
to be in the middle of other "fast poll" registers.

Readings update when their corresponding registers are read, though the `last_updated` time
may not update if the readings don't actually change.

**Do not run multiple Modbus/TCP clients with the same DTS.** This **will** result in
corrupted/spurious readings.

## Development

`mapper.py` is pure Python with no Home Assistant imports, covered by unit tests that
run without Home Assistant:

```sh
python3 -m unittest discover -s tests -v
```
