from homeassistant.components.switch import SwitchEntity

class EcomaxSwitch(SwitchEntity):
    """Switch pour contrôler EcoMax360."""
    
    def __init__(self, name):
        self._name = name
        self._state = False

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._state
