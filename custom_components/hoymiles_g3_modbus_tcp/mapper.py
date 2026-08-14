"""HA-neutral mapping from the library register catalog to sensor specs.

This module MUST NOT import homeassistant — it is unit-tested standalone.
"""

from dataclasses import dataclass

from hoymiles_g3_modbus_tcp.registers import REGISTERS


@dataclass(frozen=True)
class RegisterSpec:
    key: str
    name: str
    device: str  # battery|solar|grid_meter|inverter
    device_class: str | None  # voltage|current|power|energy|frequency|battery|temperature|reactive_power|apparent_power|None
    unit: str | None  # V|A|mA|W|kWh|Hz|%|Var|VA|kOhm|°C|None
    state_class: str | None  # measurement|total_increasing|None
    entity_category: str | None  # diagnostic|None
    precision: int
    enabled_default: bool


# unit token -> (device_class token, HA unit token); string->string, HA-free
UNIT_TABLE = {
    "V": ("voltage", "V"),
    "A": ("current", "A"),
    "mA": ("current", "mA"),
    "W": ("power", "W"),
    "kWh": ("energy", "kWh"),
    "Hz": ("frequency", "Hz"),
    "%": ("battery", "%"),
    "Var": ("reactive_power", "Var"),
    "VA": ("apparent_power", "VA"),
    "kOhm": (None, "kOhm"),
}

TEMP_KEYS = {
    "pv_ths_temp",
    "inv_ths_temp",
    "bat_ths_temp",
    "cav_temp",
    "batt_max_cell_temp",
    "batt_min_cell_temp",
}

ENERGY_KEYS = {r.key for r in REGISTERS if r.domain == "energy"}

# Grid-meter device contains exactly these (per user decision); other grid_meter-domain
# regs (meter currents/voltages/freq) fall through to the inverter device.
GRID_METER_KEYS = {"grid_meter_link", "pv_meter_link", "drm_status"}

# Low-value entities disabled by default (users can enable them).
DISABLED_KEYS = {
    "12v_aux", "5v_aux", "1_5v_aux", "relay_aux",
    "fan_1_speed", "fan_2_speed", "fan_3_speed",
    "ext_fan_1_speed", "ext_fan_2_speed", "ext_fan_3_speed", "ext_fan_4_speed",
    "powerdsp_fm_ver", "safetydsp_fm_ver",
    "sw_fault", "hw_fault",
    "pos_bus_voltage", "neg_bus_voltage", "bus_voltage", "bus_balance_current",
    "dc_inject_a", "dc_inject_b", "dc_inject_c",
    "iso_resistor", "residual_current",
    "bms_fault_code",
}


def _device(r) -> str:
    if r.domain == "battery":
        return "battery"
    if r.domain == "pv":
        return "solar"
    if r.key in GRID_METER_KEYS:
        return "grid_meter"
    return "inverter"


def _decimals(scale) -> int:
    """Decimals implied by a power-of-ten scale (value = raw / scale)."""
    n = int(round(scale))
    if n >= 1 and n == 10 ** (len(str(n)) - 1):
        return len(str(n)) - 1
    return 0


def build_register_specs(registers=REGISTERS) -> list[RegisterSpec]:
    specs = []
    for r in registers:
        key = r.key
        if key in TEMP_KEYS:
            dc, unit, sclass, cat = "temperature", "°C", "measurement", None
        elif r.unit in UNIT_TABLE:
            dc, unit = UNIT_TABLE[r.unit]
            if key in ENERGY_KEYS:
                sclass = "total_increasing"
            elif dc == "energy":
                # Rated capacity (e.g. battery_capacity), not cumulative energy.
                sclass = None
            else:
                sclass = "measurement"
            cat = None
        else:  # unitless diagnostics / fan "r/m"
            dc, unit, sclass, cat = None, None, None, "diagnostic"
        specs.append(
            RegisterSpec(
                key=key,
                name=r.label,
                device=_device(r),
                device_class=dc,
                unit=unit,
                state_class=sclass,
                entity_category=cat,
                precision=_decimals(r.scale),
                enabled_default=key not in DISABLED_KEYS,
            )
        )
    return specs
