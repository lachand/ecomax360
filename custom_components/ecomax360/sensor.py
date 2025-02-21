from homeassistant.helpers.entity import Entity
from .communication import Communication
from .parameters import THERMOSTAT, ECOMAX
import logging
_LOGGER = logging.getLogger(__name__)

message = fChargement du fichier sensor.py d'EcoMax360")
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


message = f"Démarrage de la configuration des capteurs EcoMax360")
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    comm = Communication()
    thermostat_data = comm.listenFrame("GET_THERMOSTAT") or {}
    ecomax_data = comm.listenFrame("GET_DATAS") or {}

    sensors = [EcomaxSensor(name, key, comm) for key, name in {
        **{key: f"Thermostat {key}" for key in THERMOSTAT.keys()},
        **{key: f"EcoMax {key}" for key in ECOMAX.keys()}
    }.items()]

    message = f"Nombre de capteurs détectés : {len(sensors)}"
    logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    async_add_entities(sensors, True)

class EcomaxSensor(Entity):
    previous_values = {}

    ICONS = {
        "TEMPERATURE": "mdi:thermometer",
        "JOUR": "mdi:weather-sunny",
        "NUIT": "mdi:weather-night",
        "ACTUELLE": "mdi:thermometer-check",
        "SOURCE_PRINCIPALE": "mdi:fire",
        "DEPART_RADIATEUR": "mdi:radiator",
        "ECS": "mdi:water-pump",
        "BALLON_TAMPON": "mdi:water",
        "TEMPERATURE_EXTERIEUR": "mdi:weather-partly-cloudy"
    }
    
    def __init__(self, name, param, comm):
        self._name = name
        self._param = param
        self._state = None
        self._comm = comm

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        """Retourne une icône spécifique en fonction du capteur."""
        return self.ICONS.get(self._param, "mdi:help-circle")  # Icône par défaut si non trouvé

    async def async_update(self):
        #data = self._comm.listenFrame("GET_THERMOSTAT") or {}
        data = self._comm.listenFrame("GET_DATAS") or {}
        data.update(self._comm.listenFrame("GET_DATAS") or {})
        new_value = data.get(self._param)
                             
        if new_value is not None:
            self._state = new_value
            EcomaxSensor.previous_values[self._param] = new_value
        else:
            self._state = EcomaxSensor.previous_values.get(self._param, "Inconnu")
        message = f"Capteur {self._name} mis à jour : {self._state}")
        logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
