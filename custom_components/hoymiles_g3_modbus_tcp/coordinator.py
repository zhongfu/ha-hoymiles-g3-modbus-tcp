"""Coordinator for polling the Hoymiles G3 inverter."""

import asyncio
import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

POLL_TIMEOUT = 25


class HoymilesCoordinator(DataUpdateCoordinator[dict]):
    """Poll the inverter on a fixed interval and cache the snapshot."""

    def __init__(self, hass, inverter, update_interval: int):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self.inverter = inverter

    async def _async_update_data(self):
        async with asyncio.timeout(POLL_TIMEOUT):
            return await self.inverter.poll()
