import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN

class Ecomax360ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ecomax360."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Validate the user input here
            host = user_input.get("host")
            port = user_input.get("port")
            if self._is_valid_host_port(host, port):
                return self.async_create_entry(title="ecomax360", data=user_input)
            else:
                errors["base"] = "invalid_host_or_port"

        data_schema = vol.Schema({
            vol.Required("host"): str,
            vol.Required("port"): int,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    def _is_valid_host_port(self, host, port):
        """Validate the host and port."""
        # Implémentez ici la validation spécifique de votre hôte et port
        return True
