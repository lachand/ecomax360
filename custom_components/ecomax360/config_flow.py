import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

DATA_SCHEMA = vol.Schema({
    vol.Required("host"): str,
    vol.Required("port", default=8899): int,
})

class Ecomax360ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère le formulaire d'ajout de l'intégration depuis l'UI."""

    async def async_step_user(self, user_input=None):
        """Gère l'étape de configuration."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="EcoMax360", data=user_input)

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)
