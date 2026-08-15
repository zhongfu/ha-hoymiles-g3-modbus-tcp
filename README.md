# Hoymiles G3 Modbus TCP

*AI slop disclaimer: this thing was written by deepseek-v4-flash-0731 with input from me.*

Home Assistant integration for the **Hoymiles G3 hybrid inverter** (HIT-G3 series)
read through a **DTS-WL-G3 Ethernet stick**. It reads the inverter over Modbus/TCP
and shows its live measurements in Home Assistant.

The integration is **read-only** — it never writes to the inverter.

## Supported hardware

- Hoymiles HIT-G3 hybrid inverters read through a **DTS-WL-G3 Ethernet stick** over
  Modbus/TCP.

## Install

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zhongfu&repository=ha-hoymiles-g3-modbus-tcp&category=integration)

Add this repository as a **custom repository** (HACS → ⋯ → **Custom repositories** →
`https://github.com/zhongfu/ha-hoymiles-g3-modbus-tcp`, category **Integration**),
install **"Hoymiles G3 Modbus TCP"** from HACS, then add it via **Settings → Devices &
Services → Add Integration**.

### Manual

1. Copy the `custom_components/hoymiles_g3_modbus_tcp` folder into your Home
   Assistant `config/custom_components/` folder.
2. Restart Home Assistant.
3. Add the integration via **Settings → Devices & Services → Add Integration →
   "Hoymiles G3 Modbus TCP"** and enter your Ethernet stick's IP address. Defaults:
   port `502`, unit `1`, and a poll interval of 30 seconds. You can change any of
   these later under **Settings → Devices & Services → ⋯ → Options** (the integration
   reloads to apply the new settings).

## What you get

Your inverter's data is organised into **four devices**:

| Device | Shows |
|--------|-------|
| **Battery** | battery state and measurements — charge level, voltage, current, power, cell temperatures, etc. |
| **Solar** | PV per-string and total power, voltage and current |
| **Grid Meter** | the external grid and PV meter readings (per-phase and total voltage, current, power, power factor, frequency, link status) |
| **Inverter** | everything else — mains/AC/backup/generator/energy, status and diagnostics |

Read-only settings (export limits, SOC range, EMS/SOC limits, EPS/PV island mode,
battery type, topology, …) show up as **Configuration** controls (sliders and
dropdowns) on the **Inverter** device, keeping them out of the live readings. Because
data flows one way, those controls are read-only for now.

Nothing is dropped — every reading is exposed. Diagnostics you rarely need (fans, aux
rails, fault codes, bus voltages, firmware versions, …) are **off by default** so they
don't clutter the UI; turn any of them on from the entity settings. Energy readings
are shown as lifetime totals.

## Polling

Fast-moving measurements (powers, currents, voltages, frequency, meters) refresh
often — every `poll_interval` (default 30 seconds). A slower **full poll** — every
`full_poll_interval` (default 300 seconds / 5 minutes) — reads everything else:
energy totals, status, battery parameters and the settings controls. Each reading
only updates when it's actually polled, so the "last updated" time you see reflects
the real read cadence.

If the same inverter is also being polled by the `hoymiles-g3-modbus-tcp` tool, you
may occasionally see brief reading errors on the stick — the integration tolerates
these.

## Development

`mapper.py` is pure Python with no Home Assistant imports, covered by unit tests that
run without Home Assistant:

```sh
python3 -m unittest discover -s tests -v
```

Requires `hoymiles-g3-modbus-tcp` (and `pymodbus`) importable — either pip-installed
or present as a sibling folder `../hoymiles-g3-modbus-tcp`.
