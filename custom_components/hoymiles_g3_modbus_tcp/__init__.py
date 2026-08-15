"""The Hoymiles G3 Modbus TCP integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from hoymiles_g3_modbus_tcp import Inverter, InverterConfig

from .const import (
    CONF_FULL_POLL_INTERVAL,
    CONF_HOST,
    CONF_POLL_INTERVAL,
    CONF_PORT,
    CONF_UNIT,
    DEFAULT_FULL_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)
from .coordinator import HoymilesCoordinator

PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.SELECT]


def _setting(entry: ConfigEntry, key: str, default):
    """Resolve a setting from entry options, falling back to entry data."""
    return entry.options.get(key, entry.data.get(key, default))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Hoymiles G3 inverter from a config entry."""
    inverter = Inverter(
        InverterConfig(
            host=_setting(entry, CONF_HOST, ""),
            port=_setting(entry, CONF_PORT, 502),
            unit=_setting(entry, CONF_UNIT, 1),
        )
    )
    try:
        await inverter.connect()
        await inverter.detect()
    except ConfigEntryNotReady:
        raise
    except Exception as err:  # noqa: BLE001 - transient comm errors -> HA retries
        raise ConfigEntryNotReady(
            f"Failed to connect to inverter: {err}"
        ) from err
    coordinator = HoymilesCoordinator(
        hass,
        inverter,
        _setting(entry, CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
        _setting(entry, CONF_FULL_POLL_INTERVAL, DEFAULT_FULL_POLL_INTERVAL),
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
