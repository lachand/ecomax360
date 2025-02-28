import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .coordinator import EcomaxCoordinator
from .api import EcoMAXAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("Initialisation de ecomax360")

    api = EcoMAXAPI()
    coordinator = EcomaxCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN] = {"coordinator": coordinator, "api": api}
    hass.config_entries.async_setup_platforms(entry, ["sensor", "climate"])

    return True
