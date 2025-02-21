from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNKNOWN
from .communication import Communication
from .parameters import THERMOSTAT, ECOMAX
from .trame import Trame
import logging
_LOGGER = logging.getLogger(__name__)

message = f"hargement du fichier sensor.py d'EcoMax360"
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


message = f"Démarrage de la configuration des capteurs EcoMax360"
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    comm = Communication()
    trame = Trame("64 00", "20 00", "40", "c0", "647800","").build()
    thermostat_data = comm.request(trame,THERMOSTAT, "265535445525f78343","c0") or {}
    ecomax_data = comm.listenFrame("GET_DATAS") or {}

    sensors = [EcomaxSensor(name, key, comm) for key, name in {
        **{key: f"Thermostat {key}" for key in THERMOSTAT.keys()},
        **{key: f"EcoMax {key}" for key in ECOMAX.keys()}
    }.items()]

    message = f"Nombre de capteurs détectés : {len(sensors)}"
    logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    async_add_entities(sensors, True)

class EcomaxSensor(SensorEntity):
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

    UNIT_MAPPING = {
        "TEMPERATURE": "°C",
        "ACTUELLE": "°C",
        "DEPART_RADIATEUR": "°C",
        "ECS": "°C",
        "BALLON_TAMPON": "°C",
        "TEMPERATURE_EXTERIEUR": "°C"
    }
    
    def __init__(self, name, param, comm):
        self._name = name
        self._param = param
        self._state = None
        self._comm = comm
        self._attr_native_unit_of_measurement = self.UNIT_MAPPING.get(param)
        self._attr_device_class = "temperature" if self._attr_native_unit_of_measurement == "°C" else None
        self._attr_state_class = "measurement" if self._attr_native_unit_of_measurement else None

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
        trame = Trame("64 00", "20 00", "40", "c0", "647800","").build()
        data = comm.request(trame,THERMOSTAT, "265535445525f78343","c0") or {}
        data.update(self._comm.listenFrame("GET_DATAS") or {})
        new_value = data.get(self._param)
                             
        if new_value is not None:
            try:
                self._state = round(float(new_value), 2)
                EcomaxSensor.previous_values[self._param] = self._state
            except ValueError:
                self._state = STATE_UNKNOWN
        else:
            self._state = EcomaxSensor.previous_values.get(self._param, STATE_UNKNOWN)
        message = f"Capteur {self._name} mis à jour : {self._state}"
        logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
