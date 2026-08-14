"""Config flow for the Hoymiles G3 Modbus TCP integration."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from hoymiles_g3_modbus_tcp import Inverter, InverterConfig

from .const import (
    CONF_POLL_INTERVAL,
    CONF_PORT,
    CONF_UNIT,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_UNIT,
    DOMAIN,
)


class HoymilesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hoymiles G3."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                inv = Inverter(
                    InverterConfig(
                        host=user_input[CONF_HOST],
                        port=user_input[CONF_PORT],
                        unit=user_input[CONF_UNIT],
                    )
                )
                await inv.connect()
                await inv.detect()
                await inv.close()
            except Exception:  # noqa: BLE001 - connect/detect failures -> unreachable
                errors["base"] = "cannot_connect"
            else:
                uid = (
                    f"{user_input[CONF_HOST]}:"
                    f"{user_input[CONF_PORT]}:{user_input[CONF_UNIT]}"
                )
                await self.async_set_unique_id(uid)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}",
                    data=user_input,
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Optional(CONF_UNIT, default=DEFAULT_UNIT): int,
                    vol.Optional(
                        CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL
                    ): int,
                }
            ),
            errors=errors,
        )
