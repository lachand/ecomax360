"""Home Assistant integration for EcoMAX360 controllers.

This module contains the entry points required by Home Assistant to set
up and tear down the integration.  It defines the async setup of the
integration as well as the configuration entry handling.  The
integration makes use of a :class:`~homeassistant.helpers.update_coordinator.DataUpdateCoordinator`
to poll the device for new data at regular intervals.  The coordinator
holds an instance of :class:`~custom_components.ecomax360.api.client.EcoMaxClient` which
is responsible for the low–level TCP communication.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS, CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .api.client import EcoMaxClient
from .coordinator import EcoMaxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the EcoMAX360 component via YAML (deprecated).

    This integration is designed to be configured via the UI config flow.
    The YAML configuration remains for backward compatibility but will
    simply store the values and not initialise the integration.  Users
    should migrate to the UI configuration.
    """
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EcoMAX360 from a config entry.

    This method is called by Home Assistant when the user adds a new
    EcoMAX360 integration via the UI.  It is responsible for creating
    the TCP client and the data coordinator, kicking off the first data
    refresh and forwarding the entry to the appropriate platform
    components.
    """
    hass.data.setdefault(DOMAIN, {})

    # Extract configuration from the entry
    host: str = entry.data.get(CONF_HOST)
    port: int = int(entry.data.get(CONF_PORT))
    scan_interval: int = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    _LOGGER.debug("Setting up EcoMAX360 entry %s for %s:%s", entry.entry_id, host, port)

    # Initialise the client and coordinator
    client = EcoMaxClient(host, port)
    coordinator = EcoMaxDataUpdateCoordinator(hass, client, scan_interval)

    try:
        # Perform the first refresh to populate initial data
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:  # noqa: BLE001
        # If the first refresh fails, the entry will be marked as not ready
        _LOGGER.error("Failed to initialise EcoMAX360 entry: %s", err)
        return False

    # Store the coordinator and client so they can be accessed by the platforms
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    # Forward the entry to the supported platforms.  Each platform
    # implements an ``async_setup_entry`` to set up its entities.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options updates so that we can reload the entry when
    # options change (e.g. polling interval).
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle updates to the config entry options.

    When the user modifies options via the options flow (e.g. changing
    the scan interval), Home Assistant will reload the entry.  This
    callback schedules a reload of the entry.
    """
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    This method is called when the user removes the integration.  It
    forwards the unload to all platforms, then cleans up the stored
    coordinator and client.  The client's connection will be closed
    automatically when the coordinator is garbage collected.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, {})
        client: EcoMaxClient | None = data.get("client")
        if client is not None:
            await client.async_disconnect()
    return unload_ok