from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import SUPPORT_TARGET_TEMPERATURE
from homeassistant.const import TEMP_CELSIUS
from .communication import Communication
from .utils import validate_value
import from .trame import Trame

THERMOSTAT = {
    "MODE": {"index" : 29, "type" : int, "values": {
        0 : "Auto Jour",
        1 : "Nuit",
        2 : "Jour",
        3 : "Exterieur",
        4 : "Aération",
        5 : "Fête",
        6 : "Vacances",
        7 : "Hors-gel"
    }},
    "AUTO": {"index" : 14, "type" : int},
    "TEMPERATURE": {"index" : 31, "type" : float},
    "JOUR": {"index" : 41, "type" : float},
    "NUIT": {"index" : 46, "type" : float},
    "HORS_GEL": {"index" : 51, "type" : float},
    "ACTUELLE": {"index" : 36, "type" : float},
}

class EcomaxClimate(ClimateEntity):
    """Contrôle du chauffage via EcoMax360."""
    
    def __init__(self):
        self._name = "Chauffage EcoMax360"
        self._temperature = None
        self._target_temperature = None
        self._communication = Communication()
    
    @property
    def name(self):
        return self._name
    
    @property
    def temperature_unit(self):
        return TEMP_CELSIUS
    
    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE
    
    @property
    def current_temperature(self):
        return self._temperature
    
    @property
    def target_temperature(self):
        return self._target_temperature
    
    def update(self):
        """Met à jour les valeurs du thermostat."""
        try:
            self._communication.connect()
            trame = Trame("64 00", "20 00", "40", "c0", "647800","").build()
            datas_t = self._communication.request(trame,THERMOSTAT, "265535445525f78343","c0")
            self._communication.close()
            self._temperature = data_t['TEMPERATURE']
            self._target_temperature = data_t['ACTUELLE']
        except Exception as e:
            self._temperature = None
            self._target_temperature = None
            print(f"Erreur lors de la récupération des données : {e}")
    
    def set_temperature(self, **kwargs):
        """Modifie la température cible du thermostat."""
        if "temperature" in kwargs:
            new_temp = kwargs["temperature"]
            try:
                self._communication.connect()
                value_hex = validate_value(param_key, value)
                trame = Trame("64 00","20 00","29","a9","01 20 01", value_hex).build()
                self._communication.send(trame)
                self._target_temperature = new_temp
            except Exception as e:
                print(f"Erreur lors de la modification de la température : {e}")
