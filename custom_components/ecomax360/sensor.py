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
    trame = Trame("FFFF", "0100", "40", "c0", "640000","").build()
    comm = Communication()
    comm.connect()
    datas = comm.request(trame, ECOMAX, "3130303538343230303400", "c0")
    _LOGGER.info(trame)
    _LOGGER.info(datas)
    comm.close()

    sensors = [EcomaxSensor(name, key, comm) for key, name in {
            **{key: f"EcoMax {key}" for key in ["BALLON_TAMPON"]}#ECOMAX.keys()}
    }.items()]

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
        trame = Trame("FFFF", "0100", "40", "c0", "640000","").build()
        comm = Communication()
        comm.connect()
        data = comm.request(trame, ECOMAX, "3130303538343230303400", "c0")
        new_value = data.get(self._param)
                             
        if new_value is not None and new_value > 5 and new_value < 105:
            try:
                self._state = round(float(new_value), 2)
                EcomaxSensor.previous_values[self._param] = self._state
            except ValueError:
                self._state = STATE_UNKNOWN
        else:
            self._state = EcomaxSensor.previous_values.get(self._param, STATE_UNKNOWN)
        _LOGGER.info(data)
        comm.close()
