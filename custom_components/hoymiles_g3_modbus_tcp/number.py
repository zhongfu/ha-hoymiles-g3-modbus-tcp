"""Number platform: read-only configuration registers (settings domain).

Each entity is a Number under EntityCategory.CONFIG, so HA groups it in the
Configuration section of the Inverter device. The integration is read-only, so
any change attempt is rejected; this guard is a placeholder that can be swapped
for a real write once the underlying library gains write support.
"""

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER, NAME
from .mapper import build_control_specs

_LOGGER = logging.getLogger(__name__)

UNIT_MAP = {
    "%": PERCENTAGE,
    "W": UnitOfPower.WATT,
    "kWh": UnitOfEnergy.KILO_WATT_HOUR,
}


class HoymilesConfigNumber(NumberEntity):
    """A read-only settings register exposed as a Number control."""

    def __init__(self, coordinator, spec, device_info, entry_unique_id):
        self.coordinator = coordinator
        self._spec = spec
        self._attr_unique_id = f"{entry_unique_id}_{spec.key}"
        self._attr_name = spec.name
        self._attr_device_info = device_info
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_unit_of_measurement = UNIT_MAP.get(spec.unit)
        self._attr_native_min_value = spec.min_value
        self._attr_native_max_value = spec.max_value
        self._attr_native_step = spec.step
        self._attr_suggested_display_precision = spec.precision
        self._attr_should_poll = False
        self._last_ts = None  # last actual register-read epoch this entity has shown

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
        self._handle_coordinator_update()

    def _handle_coordinator_update(self):
        ts = self.coordinator.inverter.last_updated(self._spec.key)
        if ts is None or ts == self._last_ts:
            return  # register not freshly read this tick; keep last_updated stable
        self._last_ts = ts
        self._attr_native_value = self.coordinator.data.get(self._spec.key)
        self.async_write_ha_state()

    async def async_set_native_value(self, value):
        # Read-only: the library cannot write to the inverter. Reject the change.
        _LOGGER.warning(
            "Rejected setting %s to %s: integration is read-only",
            self.entity_id,
            value,
        )
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    info = coordinator.inverter.device_info
    model = info.inverter_model or NAME
    device = DeviceInfo(
        identifiers={(DOMAIN, f"{entry.unique_id}_inverter")},
        name=f"{model} Inverter",
        manufacturer=MANUFACTURER,
        model=model,
    )
    specs = [s for s in build_control_specs() if s.kind == "number"]
    async_add_entities(
        HoymilesConfigNumber(coordinator, s, device, entry.unique_id) for s in specs
    )
