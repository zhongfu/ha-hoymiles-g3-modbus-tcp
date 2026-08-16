"""Unit tests for the HA-neutral register mapper (no Home Assistant required)."""

import sys
from pathlib import Path

# Make the integration package and the library importable without a pip install.
# (conftest.py mirrors this for pytest; unittest discovery does not load conftest.)
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "custom_components" / "hoymiles_g3_modbus_tcp"))
_LIB = _ROOT.parent / "hoymiles-g3-modbus-tcp"
if _LIB.is_dir():
    sys.path.insert(0, str(_LIB))

import unittest  # noqa: E402

from hoymiles_g3_modbus_tcp.registers import REGISTERS  # noqa: E402

import mapper  # noqa: E402
from mapper import (  # noqa: E402
    DISABLED_KEYS,
    ENERGY_KEYS,
    FAST_KEYS,
    TEMP_KEYS,
    build_control_specs,
)
class TestMapper(unittest.TestCase):
    def setUp(self):
        self.specs = mapper.build_register_specs()
        self.by_key = {s.key: s for s in self.specs}

    def test_count_matches_catalog(self):
        self.assertEqual(len(self.specs), len(REGISTERS))
        self.assertEqual(set(self.by_key), {r.key for r in REGISTERS})
        # unique keys -> one spec per register
        self.assertEqual(len(self.by_key), len(self.specs))

    def test_device_grouping(self):
        for r in REGISTERS:
            spec = self.by_key[r.key]
            if r.domain == "battery":
                self.assertEqual(spec.device, "battery", r.key)
            elif r.domain == "pv":
                self.assertEqual(spec.device, "solar", r.key)
            elif r.domain == "grid_meter":
                self.assertEqual(spec.device, "grid_meter", r.key)
            else:
                self.assertEqual(spec.device, "inverter", r.key)

    def test_all_devices_present(self):
        devices = {s.device for s in self.specs}
        self.assertEqual(
            devices,
            {"battery", "solar", "grid_meter", "inverter"},
        )

    def test_controls_cover_settings_domain(self):
        controls = mapper.build_control_specs()
        cby = {c.key: c for c in controls}
        settings_keys = {r.key for r in REGISTERS if r.domain == "settings"}
        self.assertEqual(set(cby), settings_keys)
        self.assertEqual(len(controls), len(settings_keys))

    def test_control_kinds_match_enum(self):
        for c in mapper.build_control_specs():
            r = next(x for x in REGISTERS if x.key == c.key)
            if r.enum is not None:
                self.assertEqual(c.kind, "select", c.key)
                self.assertEqual(c.options, tuple(r.enum[i] for i in sorted(r.enum)), c.key)
            else:
                self.assertEqual(c.kind, "number", c.key)
                self.assertIsNone(c.options, c.key)

    def test_number_controls_have_sane_bounds(self):
        for c in mapper.build_control_specs():
            if c.kind != "number":
                continue
            self.assertGreaterEqual(c.min_value, 0, c.key)
            self.assertGreater(c.max_value, c.min_value, c.key)
            self.assertGreater(c.step, 0, c.key)

    def test_valid_units(self):
        allowed = {"V", "A", "mA", "W", "kWh", "Hz", "%", "Var", "VA", "kOhm", "°C", None}
        for s in self.specs:
            self.assertIn(s.unit, allowed, s.key)

    def test_temperature_keys(self):
        for key in TEMP_KEYS:
            s = self.by_key[key]
            self.assertEqual(s.device_class, "temperature", key)
            self.assertEqual(s.unit, "°C", key)
            self.assertEqual(s.state_class, "measurement", key)

    def test_energy_keys_total_increasing(self):
        for r in REGISTERS:
            if r.domain == "energy" and r.unit == "kWh":
                s = self.by_key[r.key]
                self.assertEqual(s.state_class, "total_increasing", r.key)

    def test_numeric_flag_matches_enum_bitmap(self):
        for r in REGISTERS:
            s = self.by_key[r.key]
            self.assertEqual(
                s.numeric, (r.enum is None and r.bitmap is None), r.key
            )

    def test_energy_power_is_measurement(self):
        # Energy-domain instantaneous power registers must never be counters.
        for r in REGISTERS:
            if r.domain == "energy" and r.unit == "W":
                s = self.by_key[r.key]
                self.assertEqual(s.device_class, "power", r.key)
                self.assertEqual(s.state_class, "measurement", r.key)
                self.assertIsNone(s.entity_category, r.key)

    def test_unitless_non_config_are_diagnostic(self):
        for s in self.specs:
            if s.unit is None:
                self.assertEqual(s.entity_category, "diagnostic", s.key)

    def test_battery_soc(self):
        s = self.by_key["battery_soc"]
        self.assertEqual(s.device_class, "battery")
        self.assertEqual(s.unit, "%")
        self.assertEqual(s.state_class, "measurement")

    def test_energy_device_class_state_class(self):
        # HA requires energy device class to use total/total_increasing, never
        # measurement; rated capacities are None.
        for s in self.specs:
            if s.device_class == "energy":
                self.assertIn(s.state_class, ("total_increasing", None), s.key)
        # battery_capacity is a rated capacity, not cumulative energy.
        self.assertIsNone(self.by_key["battery_capacity"].state_class)

    def test_precision_matches_scale(self):
        def decimals(scale):
            n = int(round(scale))
            if n >= 1 and n == 10 ** (len(str(n)) - 1):
                return len(str(n)) - 1
            return 0

        for r in REGISTERS:
            self.assertEqual(self.by_key[r.key].precision, decimals(r.scale), r.key)
        # spot-check the human-meaningful cases
        self.assertEqual(self.by_key["grid_voltage_a"].precision, 1)   # scale 10
        self.assertEqual(self.by_key["pv1_current"].precision, 2)      # scale 100
        self.assertEqual(self.by_key["battery_soc"].precision, 0)      # scale 1

    def test_enabled_default_exact(self):
        for r in REGISTERS:
            spec = self.by_key[r.key]
            self.assertEqual(
                spec.enabled_default,
                r.key not in DISABLED_KEYS,
                r.key,
            )

    def test_disabled_superset_of_catalog(self):
        # Every disabled key must actually exist in the catalog.
        catalog_keys = {r.key for r in REGISTERS}
        self.assertLessEqual(DISABLED_KEYS, catalog_keys)

    def test_no_config_category(self):
        # HA disallows EntityCategory.CONFIG on sensor entities.
        for s in self.specs:
            self.assertIn(s.entity_category, (None, "diagnostic"), s.key)

    def test_fast_keys_follows_physical_fast_coverage(self):
        """FAST_KEYS classifies by poll coverage, not semantic group."""
        self.assertTrue(FAST_KEYS, "FAST_KEYS must not be empty")
        fast_ranges = ((0, 123), (1800, 1924), (2000, 2246), (30000, 30021))

        def _in_fast(r):
            return any(lo <= r.addr < hi for lo, hi in fast_ranges)

        fast_inputs = [r for r in REGISTERS if r.kind == "input" and _in_fast(r)]
        self.assertTrue(fast_inputs, "no fast-range input register found")
        fast_key = next(r.key for r in fast_inputs)
        self.assertIn(fast_key, FAST_KEYS, fast_key)

        holdings = [r for r in REGISTERS if r.kind == "holding"]
        self.assertTrue(holdings, "no holding register found")
        full_key = next(r.key for r in holdings)
        self.assertNotIn(full_key, FAST_KEYS, full_key)

        self.assertIn("pv_total_power", FAST_KEYS)

        overlaps = [
            r.key
            for r in REGISTERS
            if r.domain in ("diagnostics", "status") and _in_fast(r)
            and r.key in FAST_KEYS
        ]
        self.assertTrue(
            overlaps,
            "status/diagnostics register inside a fast range must be fast-class",
        )


if __name__ == "__main__":
    unittest.main()
