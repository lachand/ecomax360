import logging
from homeassistant.helpers.discovery import load_platform

_LOGGER = logging.getLogger(__name__)
DOMAIN = "ecomax360"

def setup(hass, config):
    """Configuration de l'intégration."""
    _LOGGER.info("Démarrage de EcoMax360")
    load_platform(hass, "sensor", DOMAIN, {}, config)
    #load_platform(hass, "climate", DOMAIN, {}, config)
    #load_platform(hass, "switch", DOMAIN, {}, config)
    return True
