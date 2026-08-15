"""Coordinator for polling the Hoymiles G3 inverter."""

import asyncio
import logging
from datetime import timedelta
from time import monotonic

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

POLL_TIMEOUT = 25


class HoymilesCoordinator(DataUpdateCoordinator[dict]):
    """Two-tier poller: fast measurements frequently, a full poll periodically."""

    def __init__(self, hass, inverter, fast_interval: int, full_interval: int):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=fast_interval),
        )
        self.inverter = inverter
        self._full_interval = full_interval
        self._next_full = None

    async def _async_update_data(self):
        async with asyncio.timeout(POLL_TIMEOUT):
            now = monotonic()
            if self._next_full is None or now >= self._next_full:
                # First poll, then every full_interval: refresh every register
                # (fast + energy/status/battery/diagnostics/settings groups).
                self._next_full = now + self._full_interval
                return await self.inverter.poll_all()
            # Fast tier: only the rapidly-changing measurement registers.
            return await self.inverter.poll_group("fast")
