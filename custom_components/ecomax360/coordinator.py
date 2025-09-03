"""Data update coordinator for the EcoMAX360 integration.

The coordinator encapsulates the logic required to periodically poll the
EcoMAX controller for its current state.  It uses the
:class:`~custom_components.ecomax360.api.client.EcoMaxClient` to listen
for broadcast frames matching the ``GET_DATAS`` parameter and exposes
the decoded data via the :attr:`data` attribute.  Entities in this
integration should inherit from :class:`homeassistant.helpers.update_coordinator.CoordinatorEntity`
and read values from ``self.coordinator.data``.

The update interval can be configured by the user via the options flow
or falls back to :data:`~custom_components.ecomax360.const.DEFAULT_SCAN_INTERVAL`.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api.client import EcoMaxClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EcoMaxDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Class to manage fetching EcoMAX data from a single controller."""

    def __init__(self, hass: HomeAssistant, client: EcoMaxClient, scan_interval: int) -> None:
        self.client: EcoMaxClient = client
        # Note: update_interval must be a timedelta
        interval = timedelta(seconds=scan_interval)
        super().__init__(
            hass,
            _LOGGER,
            name="EcoMAX360 Data Coordinator",
            update_interval=interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch the latest data from the EcoMAX controller.

        This method is called by Home Assistant at each ``update_interval``.
        It listens for a frame matching the ``GET_DATAS`` parameter and
        returns the decoded values.  If no frame is found, an empty
        dictionary is returned.  Any exceptions raised are converted into
        :class:`UpdateFailed` to inform Home Assistant of an error state.

        Returns
        -------
        dict
            A mapping of parameter keys (e.g. ``"DEPART_RADIATEUR"``) to
            their decoded values.
        """
        try:
            # Ensure the connection is open
            await self.client.async_connect()
            data = await self.client.listen_frame("GET_DATAS")
            # Disconnect after each fetch to free resources; the client will
            # reconnect on the next call automatically.
            await self.client.async_disconnect()
            return data or {}
        except Exception as err:  # noqa: BLE001
            # Any exception is wrapped into UpdateFailed so that HA can
            # handle it properly and mark the entity as unavailable.
            raise UpdateFailed(f"Error fetching EcoMAX data: {err}") from err