"""Configuration flow for the EcoMAX360 integration.

This module implements the UI configuration flow used by Home Assistant to
set up the EcoMAX360 integration.  The flow prompts the user for the
connection details (host and port) and attempts to validate that a
connection can be established.  An options flow is also provided to
allow adjustments to the polling interval and connection details after
initial setup.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .api.client import EcoMaxClient

_LOGGER = logging.getLogger(__name__)


async def _async_validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> None:
    """Validate the user input allows us to connect to the controller.

    This function attempts to open a TCP connection to the provided host
    and port.  If the connection fails, it raises a ValueError.  The
    connection is closed immediately after being established.
    """
    host: str = data[CONF_HOST]
    port: int = int(data[CONF_PORT])
    client = EcoMaxClient(host, port)
    try:
        await client.async_connect()
    finally:
        await client.async_disconnect()


class Ecomax360ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EcoMAX360."""

    VERSION = 1

    def __init__(self) -> None:
        self._errors: Dict[str, str] = {}

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step of the config flow."""
        self._errors.clear()
        if user_input is not None:
            # Prevent duplicate entries for the same host/port combination
            for entry in self._async_current_entries():
                if (
                    entry.data.get(CONF_HOST) == user_input[CONF_HOST]
                    and int(entry.data.get(CONF_PORT)) == int(user_input[CONF_PORT])
                ):
                    return self.async_abort(reason="already_configured")
            # Validate connection
            try:
                await _async_validate_input(self.hass, user_input)
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Error connecting to EcoMAX360: %s", err)
                self._errors["base"] = "cannot_connect"
            if not self._errors:
                return self.async_create_entry(title="EcoMAX360", data=user_input)

        # Show the form (either initial or with errors)
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): str,
                vol.Required(CONF_PORT, default=(user_input or {}).get(CONF_PORT, 8899)): int,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=self._errors,
        )

    async def async_step_import(self, import_config: Dict[str, Any]) -> FlowResult:
        """Handle YAML configuration import.

        Home Assistant allows integrations to import configuration from YAML
        into config entries.  This method checks for duplicates and then
        creates a new entry using the same logic as the user flow.
        """
        # Check for existing entries with the same host/port
        for entry in self._async_current_entries():
            if (
                entry.data.get(CONF_HOST) == import_config.get(CONF_HOST)
                and int(entry.data.get(CONF_PORT)) == int(import_config.get(CONF_PORT))
            ):
                return self.async_abort(reason="already_configured")
        return await self.async_step_user(import_config)

    async def async_step_onboarding(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Handle the flow step during Home Assistant onboarding.

        During onboarding, we simply reuse the user step.
        """
        return await self.async_step_user(user_input)

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> "Ecomax360OptionsFlow":
        return Ecomax360OptionsFlow(config_entry)


class Ecomax360OptionsFlow(config_entries.OptionsFlow):
    """Handle an options flow for EcoMAX360."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Manage the options for the integration.

        This step is invoked when the user chooses to configure options
        from the integration's configuration page.  It allows updating
        the host, port and polling interval.  Changes are persisted by
        updating the underlying config entry.
        """
        if user_input is not None:
            # Read the new values from the form
            new_host: str = user_input[CONF_HOST]
            new_port: int = int(user_input[CONF_PORT])
            scan_interval: int | None = user_input.get(CONF_SCAN_INTERVAL)
            # Build the new data and options dicts
            new_data = {
                CONF_HOST: new_host,
                CONF_PORT: new_port,
            }
            new_options = {
                CONF_SCAN_INTERVAL: scan_interval
            } if scan_interval is not None else {}
            # Persist changes via update_entry
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data,
                options=new_options,
            )
            return self.async_create_entry(title="EcoMAX360 Options", data={})

        # Prepopulate form with current values
        current_data = self.config_entry.data
        current_options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=current_data.get(CONF_HOST, "")): str,
                    vol.Required(CONF_PORT, default=int(current_data.get(CONF_PORT))): int,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current_options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): int,
                }
            ),
        )