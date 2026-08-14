"""The Hoymiles G3 Modbus TCP integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from hoymiles_g3_modbus_tcp import Inverter, InverterConfig

from .const import (
    CONF_HOST,
    CONF_POLL_INTERVAL,
    CONF_PORT,
    CONF_UNIT,
    DOMAIN,
)
from .coordinator import HoymilesCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Hoymiles G3 inverter from a config entry."""
    cfg = entry.data
    inverter = Inverter(
        InverterConfig(
            host=cfg[CONF_HOST],
            port=cfg[CONF_PORT],
            unit=cfg[CONF_UNIT],
        )
    )
    await inverter.connect()
    await inverter.detect()
    coordinator = HoymilesCoordinator(
        hass, inverter, cfg[CONF_POLL_INTERVAL]
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.inverter.close()
    return ok
