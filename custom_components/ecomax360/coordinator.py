import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from .api import EcoMAXAPI
from .parameters import PARAMETER

_LOGGER = logging.getLogger(__name__)

class EcomaxCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api: EcoMAXAPI):
        super().__init__(
            hass, _LOGGER, name="ecomax360",
            update_method=self.async_update_data,
            update_interval=timedelta(seconds=300),
        )
        self.api = api

    async def async_update_data(self):
        try:
            _LOGGER.debug("Mise à jour des données ecoMAX360...")
            trame = "64 00 20 00 40 c0 647800"
            data = self.api.request(trame, PARAMETER["GET_DATAS"]["dataStruct"], PARAMETER["GET_DATAS"]["dataToSearch"], "c0")

            if not data:
                raise UpdateFailed("Aucune donnée reçue de ecoMAX360")

            _LOGGER.info("Données mises à jour : %s", data)
            return data
        except Exception as err:
            _LOGGER.error("Erreur lors de la mise à jour : %s", err)
            raise UpdateFailed(f"Échec de mise à jour des données ecoMAX360: {err}")
