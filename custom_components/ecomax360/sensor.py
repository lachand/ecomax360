import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from .api import EcoMAXAPI
from .parameters import ECOMAX, PARAMETER, DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = EcoMAXAPI()
    coordinator = hass.data[DOMAIN]["coordinator"]
    sensors = [EcomaxSensor(api, coordinator, key, name) for key, name in ECOMAX.items()]
    async_add_entities(sensors)

class EcomaxSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, api, coordinator, key, description):
        super().__init__(coordinator)
        self.api = api
        self.key = key
        self._attr_name = description["index"]
        self._attr_unique_id = f"ecomax360_{key}"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE if "temperature" in key.lower() else None
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS if "temperature" in key.lower() else PERCENTAGE

    @property
    def native_value(self):
        return self.coordinator.data.get(self.key)

    def update(self):
        trame = "6400200040c0647800"
        data = self.api.request(trame, ECOMAX, PARAMETER["GET_DATAS"]["dataToSearch"], "c0") or {}
        if data:
            self.coordinator.data = data
            _LOGGER.info("Données mises à jour: %s", data)
