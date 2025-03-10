import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import config_validation as cv
import voluptuous as vol
from .const import DOMAIN
from .coordinator import EcomaxCoordinator
from .api import EcoMAXAPI

_LOGGER = logging.getLogger(__name__)

#def setup(hass, config):
#    """Configuration de l'intégration."""
#    _LOGGER.info("Démarrage de EcoMax360")
#    #load_platform(hass, "sensor", DOMAIN, {}, config)
#    load_platform(hass, "climate", DOMAIN, {}, config)
#    #load_platform(hass, "switch", DOMAIN, {}, config)
#    return True


# Schéma de configuration YAML (si besoin)
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required("host"): cv.string,
                vol.Required("port"): cv.port
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Configurer ecomax360 à partir du fichier YAML."""
    if DOMAIN in config:
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN]["config"] = config[DOMAIN]
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurer ecomax360 depuis une entrée de configuration (UI)."""
    _LOGGER.info("Initialisation de ecomax360 via UI")

    # Récupérer la configuration depuis l'entrée
    host = entry.data.get("host")
    port = entry.data.get("port")

    if not host or not port:
        _LOGGER.error("La configuration de ecomax360 est incomplète. Vérifiez l'entrée de configuration.")
        return False

    _LOGGER.info(f"Connexion à EcoMAX360 - Hôte : {host}, Port : {port}")

    api = EcoMAXAPI()
    coordinator = EcomaxCoordinator(hass, api)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator, "api": api}

    #hass.config_entries.async_setup_platforms(entry, ["sensor", "climate"])
    await hass.config_entries.async_forward_entry_setup(entry, "climate")
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharger une entrée de configuration ecomax360."""
    _LOGGER.info(f"Déchargement de ecomax360 - ID d'entrée : {entry.entry_id}")

    if entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(entry.entry_id)

    #return await hass.config_entries.async_unload_platforms(entry, ["sensor", "climate"])
    return await hass.config_entries.async_unload_platforms(entry, ["sensor", "climate"])
