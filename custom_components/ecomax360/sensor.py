import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNKNOWN
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class EcomaxSensor(SensorEntity):
    """Capteur individuel d'EcoMax."""

    UNIT_MAPPING = {
        "TEMPERATURE": "°C",
        "ACTUELLE": "°C",
        "DEPART_RADIATEUR": "°C",
        "ECS": "°C",
        "BALLON_TAMPON": "°C",
        "TEMPERATURE_EXTERIEUR": "°C"
    }

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

    def __init__(self, coordinator, name, param):
        """Initialise le capteur avec le coordinateur."""
        self.coordinator = coordinator
        self._name = name
        self._param = param
        self._state = None

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
        return self.ICONS.get(self._param, "mdi:help-circle")  # Icône par défaut

    async def async_update(self):
        """Met à jour l'état du capteur à partir des données du coordinateur."""
        await self.coordinator.async_request_refresh()  # Demande la mise à jour globale
        data = self.coordinator.data or {}

        new_value = data.get(self._param)
        if new_value is not None:
            try:
                self._state = round(float(new_value), 2)
            except ValueError:
                self._state = STATE_UNKNOWN
        else:
            self._state = STATE_UNKNOWN

        _LOGGER.info(f"Capteur {self._name} mis à jour : {self._state}")

async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.info(f"Configuration capteur")
    """Configurer les capteurs pour une entrée donnée."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    await coordinator.async_config_entry_first_refresh()

    sensors = [
        EcomaxSensor(coordinator, name, key)
        for key, name in {**{key: f"EcoMax {key}" for key in coordinator.data.keys()}}.items()
    ]
    _LOGGER.info(sensors)

    async_add_entities(sensors, True)
