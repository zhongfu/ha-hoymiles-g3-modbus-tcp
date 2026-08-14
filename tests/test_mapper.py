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
    GRID_METER_KEYS,
    TEMP_KEYS,
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
            elif r.key in GRID_METER_KEYS:
                self.assertEqual(spec.device, "grid_meter", r.key)
            else:
                self.assertEqual(spec.device, "inverter", r.key)

    def test_all_devices_present(self):
        devices = {s.device for s in self.specs}
        self.assertEqual(devices, {"battery", "solar", "grid_meter", "inverter"})

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
            if r.domain == "energy":
                s = self.by_key[r.key]
                self.assertEqual(s.state_class, "total_increasing", r.key)

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


if __name__ == "__main__":
    unittest.main()
