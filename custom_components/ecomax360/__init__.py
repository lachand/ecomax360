import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import config_validation as cv
import voluptuous as vol
from .const import DOMAIN
from .coordinator import EcomaxCoordinator
from .api import EcoMAXAPI
from .communication import Communication
from .parameters import ECOMAX
from .sensor import EcomaxSensor

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
    comm = Communication()
    coordinator = EcomaxCoordinator(hass, comm)

    await coordinator.async_config_entry_first_refresh()

    sensors = [
        EcomaxSensor(coordinator, name, key)
        for key, name in {**{key: f"EcoMax {key}" for key in ECOMAX.keys()}}.items()
    ]

    logging.info(f"Nombre de capteurs détectés : {len(sensors)}")

    async_add_entities(sensors, True)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}
    #hass.data[DOMAIN][entry.entry_id] = {"api": api}

    #hass.config_entries.async_setup_platforms(entry, ["sensor", "climate"])
    await hass.config_entries.async_forward_entry_setup(entry, ["sensor", "climate"])
    #await hass.config_entries.async_forward_entry_setup(entry, "climate")

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharger une entrée de configuration ecomax360."""
    _LOGGER.info(f"Déchargement de ecomax360 - ID d'entrée : {entry.entry_id}")

    if entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(entry.entry_id)

    return await hass.config_entries.async_unload_platforms(entry, ["sensor", "climate"])
    #return await hass.config_entries.async_unload_platforms(entry, ["climate"])
