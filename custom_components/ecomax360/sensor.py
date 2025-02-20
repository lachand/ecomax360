from homeassistant.helpers.entity import Entity
from .communication import Communication
from .parameters import THERMOSTAT, ECOMAX

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    comm = Communication()
    thermostat_data = comm.listenFrame("GET_THERMOSTAT") or {}
    ecomax_data = comm.listenFrame("GET_DATAS") or {}
    
    sensors = [EcomaxSensor(name, key, comm) for key, name in {
        **{key: f"Thermostat {key}" for key in THERMOSTAT.keys()},
        **{key: f"EcoMax {key}" for key in ECOMAX.keys()}
    }.items()]
    
    async_add_entities(sensors, True)

class EcomaxSensor(Entity):
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

    async def async_update(self):
        data = self._comm.listenFrame("GET_THERMOSTAT") or {}
        data.update(self._comm.listenFrame("GET_DATAS") or {})
        self._state = data.get(self._param)
