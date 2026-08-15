"""HA-neutral mapping from the library register catalog to sensor/control specs.

This module MUST NOT import homeassistant — it is unit-tested standalone.
"""

from dataclasses import dataclass

from hoymiles_g3_modbus_tcp.registers import REGISTERS


@dataclass(frozen=True)
class RegisterSpec:
    key: str
    name: str
    domain: str
    device: str  # battery|solar|grid_meter|inverter
    device_class: str | None  # voltage|current|power|energy|frequency|battery|temperature|reactive_power|apparent_power|None
    unit: str | None  # V|A|mA|W|kWh|Hz|%|Var|VA|kOhm|°C|None
    state_class: str | None  # measurement|total_increasing|None
    entity_category: str | None  # diagnostic|None
    precision: int
    enabled_default: bool
    numeric: bool  # False for enum/bitmap registers (string/list values)


@dataclass(frozen=True)
class ControlSpec:
    """A read-only configuration control (number or select) for a settings register."""
    key: str
    name: str
    kind: str  # number|select
    unit: str | None
    precision: int
    step: float
    min_value: float
    max_value: float
    options: tuple[str, ...] | None  # select options (enum labels)
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
    "inv_ths_temp",
    "bat_ths_temp",
    "cav_temp",
    "batt_max_cell_temp",
    "batt_min_cell_temp",
}

ENERGY_KEYS = {r.key for r in REGISTERS if r.domain == "energy"}

# Low-value entities disabled by default (users can enable them).
DISABLED_KEYS = {
    "12v_aux", "5v_aux", "1_5v_aux", "relay_aux",
    "fan_1_speed", "fan_2_speed", "fan_3_speed",
    "pe_voltage",
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
    if r.domain == "grid_meter":
        return "grid_meter"
    return "inverter"


def _decimals(scale) -> int:
    """Decimals implied by a power-of-ten scale (value = raw / scale)."""
    n = int(round(scale))
    if n >= 1 and n == 10 ** (len(str(n)) - 1):
        return len(str(n)) - 1
    return 0


def _bounds(unit: str | None) -> tuple[float, float]:
    """Provisional number bounds for read-only settings registers.

    The library catalog has no per-register min/max, so these are sensible
    defaults. TODO: replace with authoritative bounds when the library gains
    write support / exposes limits.
    """
    if unit == "%":
        return 0.0, 100.0
    if unit == "W":
        return 0.0, 100_000.0
    if unit == "kWh":
        return 0.0, 10_000.0
    return 0.0, 65_535.0  # unitless 16-bit code


def build_register_specs(registers=REGISTERS) -> list[RegisterSpec]:
    """Sensor specs for every register (settings ones become controls instead)."""
    specs = []
    for r in registers:
        key = r.key
        if key in TEMP_KEYS:
            dc, unit, sclass, cat = "temperature", "°C", "measurement", None
        elif r.unit in UNIT_TABLE:
            dc, unit = UNIT_TABLE[r.unit]
            if dc == "energy" and key in ENERGY_KEYS:
                # Cumulative kWh counter (energy-domain lifetime/today registers).
                sclass = "total_increasing"
            elif dc == "energy":
                # Rated capacity (e.g. battery_capacity), not cumulative energy.
                sclass = None
            else:
                # Includes energy-domain instantaneous power registers (W).
                sclass = "measurement"
            cat = None
        else:  # unitless diagnostics / fan "r/m" / status enums
            dc, unit, sclass, cat = None, None, None, "diagnostic"
        specs.append(
            RegisterSpec(
                key=key,
                name=r.label,
                domain=r.domain,
                device=_device(r),
                device_class=dc,
                unit=unit,
                state_class=sclass,
                entity_category=cat,
                precision=_decimals(r.scale),
                enabled_default=key not in DISABLED_KEYS,
                numeric=r.enum is None and r.bitmap is None,
            )
        )
    return specs


def build_control_specs(registers=REGISTERS) -> list[ControlSpec]:
    """Map settings-domain registers to read-only Number/Select controls."""
    specs = []
    for r in registers:
        if r.domain != "settings":
            continue
        enabled = r.key not in DISABLED_KEYS
        if r.enum is not None:
            specs.append(
                ControlSpec(
                    key=r.key,
                    name=r.label,
                    kind="select",
                    unit=None,
                    precision=0,
                    step=1.0,
                    min_value=0.0,
                    max_value=0.0,
                    options=tuple(r.enum[i] for i in sorted(r.enum)),
                    enabled_default=enabled,
                )
            )
        else:
            lo, hi = _bounds(r.unit)
            specs.append(
                ControlSpec(
                    key=r.key,
                    name=r.label,
                    kind="number",
                    unit=r.unit,
                    precision=_decimals(r.scale),
                    step=1 / r.scale if r.scale else 1.0,
                    min_value=lo,
                    max_value=hi,
                    options=None,
                    enabled_default=enabled,
                )
            )
    return specs
