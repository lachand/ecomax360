from homeassistant.helpers.entity import SensorEntity

class EcomaxSensor(SensorEntity):
    """Capteur individuel d'EcoMax."""

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

        logging.info(f"Capteur {self._name} mis à jour : {self._state}")
