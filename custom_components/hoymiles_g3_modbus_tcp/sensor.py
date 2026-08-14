"""Sensor platform: one SensorEntity per register in the catalog."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    PERCENTAGE,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfTemperature,
)
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER, NAME
from .mapper import build_register_specs

DC_MAP = {
    "voltage": SensorDeviceClass.VOLTAGE,
    "current": SensorDeviceClass.CURRENT,
    "power": SensorDeviceClass.POWER,
    "energy": SensorDeviceClass.ENERGY,
    "frequency": SensorDeviceClass.FREQUENCY,
    "battery": SensorDeviceClass.BATTERY,
    "temperature": SensorDeviceClass.TEMPERATURE,
    "reactive_power": SensorDeviceClass.REACTIVE_POWER,
    "apparent_power": SensorDeviceClass.APPARENT_POWER,
}
UNIT_MAP = {
    "V": UnitOfElectricPotential.VOLT,
    "A": UnitOfElectricCurrent.AMPERE,
    "mA": UnitOfElectricCurrent.MILLIAMPERE,
    "W": UnitOfPower.WATT,
    "kWh": UnitOfEnergy.KILO_WATT_HOUR,
    "Hz": UnitOfFrequency.HERTZ,
    "%": PERCENTAGE,
    "Var": UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
    "VA": UnitOfApparentPower.VOLT_AMPERE,
    "kOhm": "kOhm",
    "°C": UnitOfTemperature.CELSIUS,
}
SC_MAP = {
    "measurement": SensorStateClass.MEASUREMENT,
    "total_increasing": SensorStateClass.TOTAL_INCREASING,
}
CAT_MAP = {
    "diagnostic": EntityCategory.DIAGNOSTIC,
}
DEVICE_SUFFIX = {
    "battery": "Battery",
    "solar": "Solar",
    "grid_meter": "Grid Meter",
    "inverter": "Inverter",
}


class HoymilesSensor(SensorEntity):
    """A single register exposed as a push-updated sensor."""

    def __init__(self, coordinator, spec, device_info, entry_unique_id):
        self.coordinator = coordinator
        self._spec = spec
        self._attr_unique_id = f"{entry_unique_id}_{spec.key}"
        self._attr_name = spec.name
        self._attr_device_info = device_info
        self._attr_device_class = DC_MAP.get(spec.device_class)
        self._attr_native_unit_of_measurement = UNIT_MAP.get(spec.unit)
        self._attr_state_class = SC_MAP.get(spec.state_class)
        self._attr_entity_category = CAT_MAP.get(spec.entity_category)
        self._attr_entity_registry_enabled_default = spec.enabled_default
        self._attr_suggested_display_precision = spec.precision
        self._attr_should_poll = False

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
        self._handle_coordinator_update()

    def _handle_coordinator_update(self):
        self._attr_native_value = self.coordinator.data.get(self._spec.key)
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    info = coordinator.inverter.device_info
    device_infos = {
        tok: DeviceInfo(
            identifiers={(DOMAIN, f"{entry.unique_id}_{tok}")},
            name=f"{info.inverter_model or NAME} {suffix}",
            manufacturer=MANUFACTURER,
            model=info.inverter_model or NAME,
        )
        for tok, suffix in DEVICE_SUFFIX.items()
    }
    specs = build_register_specs()
    async_add_entities(
        HoymilesSensor(coordinator, s, device_infos[s.device], entry.unique_id)
        for s in specs
    )
