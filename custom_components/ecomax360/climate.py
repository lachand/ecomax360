from homeassistant.components.climate import ClimateEntity

class EcomaxClimate(ClimateEntity):
    """Contrôle du chauffage via EcoMax360."""
    
    def __init__(self):
        self._name = "Chauffage EcoMax360"
        self._temperature = None

    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return "°C"
