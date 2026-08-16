"""Unit tests for the debounced per-tier availability contract.

No live inverter or Home Assistant event loop: we drive the entity
``_handle_coordinator_update`` path directly against a stub coordinator whose
``fast_failures`` / ``full_failures`` counters we set, and assert that
``available`` flips only on/after the second consecutive failure of the
governing tier and that the swap to ``async_write_ha_state`` fires only on an
actual availability transition.
"""

import sys
import unittest
from pathlib import Path

# Make the integration package and the library importable without a pip install.
# (conftest.py mirrors most of this for pytest; keep it self-contained.)
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "custom_components"))
_LIB = _ROOT.parent / "hoymiles-g3-modbus-tcp"
if _LIB.is_dir():
    sys.path.insert(0, str(_LIB))

from homeassistant.helpers.device_registry import DeviceInfo  # noqa: E402

from hoymiles_g3_modbus_tcp.registers import REGISTERS  # noqa: E402

from custom_components.hoymiles_g3_modbus_tcp.mapper import (  # noqa: E402
    FAST_KEYS,
    ControlSpec,
    RegisterSpec,
)
from custom_components.hoymiles_g3_modbus_tcp.number import (  # noqa: E402
    HoymilesConfigNumber,
)
from custom_components.hoymiles_g3_modbus_tcp.select import (  # noqa: E402
    HoymilesConfigSelect,
)
from custom_components.hoymiles_g3_modbus_tcp.sensor import (  # noqa: E402
    HoymilesSensor,
)

# Real catalog picks so the fast/full classification is exercised, not assumed.
_FAST_KEY = next(iter(FAST_KEYS))
_FULL_KEY = next(r.key for r in REGISTERS if r.key not in FAST_KEYS)

_DEVICE = DeviceInfo(identifiers={("d", "1")}, name="X")


class StubCoordinator:
    """Minimal stand-in exposing only what the availability path touches."""

    def __init__(self):
        self.fast_failures = 0
        self.full_failures = 0
        self.data = {}

        class _Inverter:
            def last_updated(self, key):  # noqa: ARG002
                return None

        self.inverter = _Inverter()

    def async_add_listener(self, fn):  # noqa: ARG002
        pass


def _sensor_spec(key):
    return RegisterSpec(
        key=key,
        name="T",
        domain="",
        device="inverter",
        device_class=None,
        unit=None,
        state_class=None,
        entity_category=None,
        precision=0,
        enabled_default=True,
        numeric=True,
    )


def _control_spec(key, kind, options=None):
    return ControlSpec(
        key=key,
        name="T",
        kind=kind,
        unit=None,
        precision=0,
        step=1.0,
        min_value=0.0,
        max_value=100.0,
        options=options,
        enabled_default=True,
    )


class TestAvailability(unittest.TestCase):
    def setUp(self):
        self.writes = []
        self.coord = StubCoordinator()
        self.fast = HoymilesSensor(self.coord, _sensor_spec(_FAST_KEY), _DEVICE, "u1")
        self.full = HoymilesSensor(self.coord, _sensor_spec(_FULL_KEY), _DEVICE, "u2")
        self.number = HoymilesConfigNumber(
            self.coord, _control_spec(_FULL_KEY, "number"), _DEVICE, "u3"
        )
        self.select = HoymilesConfigSelect(
            self.coord, _control_spec(_FULL_KEY, "select", options=("a",)), _DEVICE, "u4"
        )
        for e in (self.fast, self.full, self.number, self.select):
            e.async_write_ha_state = lambda: self.writes.append(1)

    def _drive(self, entity, fast, full):
        self.coord.fast_failures = fast
        self.coord.full_failures = full
        entity._handle_coordinator_update()

    def test_fast_sensor_debounces_on_fast_failures(self):
        # First failure tolerated (no availability flip, no write).
        self._drive(self.fast, 0, 0)
        self.assertTrue(self.fast.available)
        self.assertEqual(self.writes, [])

        self._drive(self.fast, 1, 0)
        self.assertTrue(self.fast.available)
        self.assertEqual(self.writes, [])

        # Second consecutive failure -> unavailable, write fires.
        self._drive(self.fast, 2, 0)
        self.assertFalse(self.fast.available)
        self.assertEqual(self.writes, [1])

        # First successful poll -> recovers, write fires.
        self._drive(self.fast, 0, 0)
        self.assertTrue(self.fast.available)
        self.assertEqual(self.writes, [1, 1])

    def _assert_full_only_debounce(self, entity):
        self._drive(entity, 0, 0)
        self.assertTrue(entity.available)
        self.assertEqual(self.writes, [])

        self._drive(entity, 0, 1)
        self.assertTrue(entity.available)
        self.assertEqual(self.writes, [])

        self._drive(entity, 0, 2)
        self.assertFalse(entity.available)
        self.assertEqual(self.writes, [1])

        self._drive(entity, 0, 0)
        self.assertTrue(entity.available)
        self.assertEqual(self.writes, [1, 1])

    def test_full_only_sensor_debounces_on_full_failures(self):
        self._assert_full_only_debounce(self.full)

    def test_config_number_debounces_on_full_failures(self):
        self.assertTrue(self.number._full_only)
        self._assert_full_only_debounce(self.number)

    def test_config_select_debounces_on_full_failures(self):
        self.assertTrue(self.select._full_only)
        self._assert_full_only_debounce(self.select)

    def test_tiers_are_independent(self):
        # A fast-only outage must not gate a full-only entity.
        self.coord.fast_failures = 2
        self.coord.full_failures = 1
        self.assertTrue(self.full.available)
        self.assertFalse(self.fast.available)

        # A full-only outage must not gate a fast entity.
        self.coord.fast_failures = 1
        self.coord.full_failures = 2
        self.assertTrue(self.fast.available)
        self.assertFalse(self.full.available)


if __name__ == "__main__":
    unittest.main()
