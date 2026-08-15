"""Select platform: read-only configuration registers (settings domain, enum).

Each entity is a Select under EntityCategory.CONFIG, so HA groups it in the
Configuration section of the Inverter device. The integration is read-only, so
any change attempt is rejected; this guard is a placeholder that can be swapped
for a real write once the underlying library gains write support.
"""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER, NAME
from .mapper import build_control_specs

_LOGGER = logging.getLogger(__name__)


class HoymilesConfigSelect(SelectEntity):
    """A read-only settings register exposed as a Select control."""

    def __init__(self, coordinator, spec, device_info, entry_unique_id):
        self.coordinator = coordinator
        self._spec = spec
        self._attr_unique_id = f"{entry_unique_id}_{spec.key}"
        self._attr_name = spec.name
        self._attr_device_info = device_info
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = list(spec.options)
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
        # The library maps enums to labels; only expose it if it's a known option.
        value = self.coordinator.data.get(self._spec.key)
        self._attr_current_option = value if value in self._attr_options else None
        self.async_write_ha_state()

    async def async_select_option(self, option):
        # Read-only: the library cannot write to the inverter. Reject the change.
        _LOGGER.warning(
            "Rejected selecting %s for %s: integration is read-only",
            option,
            self.entity_id,
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
    specs = [s for s in build_control_specs() if s.kind == "select"]
    async_add_entities(
        HoymilesConfigSelect(coordinator, s, device, entry.unique_id) for s in specs
    )
