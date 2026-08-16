"""Coordinator for polling the Hoymiles G3 inverter."""

import asyncio
import logging
from datetime import timedelta
from time import monotonic

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, UNAVAILABLE_AFTER_FAILURES

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
        self.fast_failures = 0   # consecutive failed polls (any tier)
        self.full_failures = 0   # consecutive failed FULL polls

    async def _async_update_data(self):
        async with asyncio.timeout(POLL_TIMEOUT):
            now = monotonic()
            is_full = self._next_full is None or now >= self._next_full
            if is_full:
                self._next_full = now + self._full_interval
            try:
                if is_full:
                    data = await self.inverter.poll_all()
                else:
                    data = await self.inverter.poll_group("fast")
            except Exception:
                # A failed poll of either tier fails fast-class registers; only
                # a failed FULL poll fails full-only registers.
                self.fast_failures += 1
                if is_full:
                    self.full_failures += 1
                if (
                    self.fast_failures == UNAVAILABLE_AFTER_FAILURES
                    or self.full_failures == UNAVAILABLE_AFTER_FAILURES
                ):
                    self.async_update_listeners()
                raise
            # Success: fast-class registers refreshed by any poll.
            self.fast_failures = 0
            # Full-only registers refreshed only by a full poll.
            if is_full:
                self.full_failures = 0
            return data
