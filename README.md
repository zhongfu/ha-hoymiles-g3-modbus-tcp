# Hoymiles G3 Modbus TCP

*AI slop disclaimer: this thing was written by deepseek-v4-flash-0731 with input from me.*

Home Assistant custom integration for the **Hoymiles G3 hybrid inverter** (HIT-G3
series via the DTS-WL-G3 Ethernet stick). It wraps the read-only PyPI library
[`hoymiles-g3-modbus-tcp`](https://pypi.org/project/hoymiles-g3-modbus-tcp/) and
exposes the inverter's input registers as Home Assistant sensors.

The integration is **read-only** — it never writes to the inverter.

## Supported hardware

- Hoymiles HIT-G3 hybrid inverters read through a **DTS-WL-G3 Ethernet stick** over
  Modbus/TCP.

## Install

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zhongfu&repository=ha-hoymiles-g3-modbus-tcp&category=integration)

Add this repository as a **custom repository** (HACS → ⋯ → **Custom repositories** →
`https://github.com/zhongfu/ha-hoymiles-g3-modbus-tcp`, category **Integration**),
then install **"Hoymiles G3 Modbus TCP"** from the HACS integrations store and add it
via **Settings → Devices & Services → Add Integration**.

### Manual

1. Copy the `custom_components/hoymiles_g3_modbus_tcp` directory into your Home
   Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration via **Settings → Devices & Services → Add Integration →
   "Hoymiles G3 Modbus TCP"** and enter the Ethernet stick's IP address. The default
   port is `502`, unit `1`, and the poll interval defaults to `30 s`.

> **Dependency:** the pinned `hoymiles-g3-modbus-tcp==0.1.1` is installed
> automatically by Home Assistant on first setup (needs internet). Since 0.1.1 it
> requires only `pymodbus>=3.13.1`, compatible with the `pymodbus==3.13.1` that Home
> Assistant ships, so it installs without manual intervention.

## What you get

Each config entry is split into **four Home Assistant devices**:

| Device | Contents |
|--------|----------|
| **Battery** | battery-domain registers (SOC, voltage, current, power, cell temps, etc.) |
| **Solar** | PV-domain registers (per-string and total power, voltage, current) |
| **Grid Meter** | `grid_meter_link`, `pv_meter_link`, `drm_status` |
| **Inverter** | everything else (grid/AC/backup/generator/energy, meter currents/voltages/freq, inverter status, diagnostics) |

All **145 registers** are exposed as sensors — nothing is dropped. Low-value diagnostic
registers (fans, aux supplies, fault codes, bus/DC-inject voltages, firmware versions,
…) are **disabled by default** so they don't clutter the UI; you can enable any of them
from the entity settings.

Every register with a unit gets an appropriate device class and `measurement` state
class; energy-domain registers are `total_increasing` kWh counters.

## Polling

The inverter is polled on the configured interval (default 30 s). Each poll reads all
registers and takes roughly two seconds. If you also run the poller from the
`hoymiles-g3-modbus-tcp` tool, both may cause occasional transient Modbus errors on the
stick — the coordinator tolerates partial reads.

## Development

The mapper (`mapper.py`) is pure Python with no Home Assistant imports and is covered
by unit tests that run without Home Assistant installed:

```sh
python3 -m unittest discover -s tests -v
```

Requires `hoymiles-g3-modbus-tcp` (and `pymodbus`) importable — either pip-installed or
present as a sibling directory `../hoymiles-g3-modbus-tcp`.
