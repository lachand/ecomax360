
import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)  # Ajout de cette ligne pour définir `_LOGGER`

class EcomaxCoordinator(DataUpdateCoordinator):
    """Coordonne la mise à jour des capteurs en évitant les requêtes multiples."""

    def __init__(self, hass, comm, entry):
        """Initialise le coordinateur avec une communication unique."""
        self._comm = comm
        self._scan_interval = entry.options.get('scan_interval', 60)
        super().__init__(
            hass,
            _LOGGER,  # Utilisation correcte du logger
            name="EcomaxCoordinator",
            update_interval=timedelta(seconds=self._scan_interval),  # Mise à jour toutes les 30 secondes
        )

    async def _async_update_data(self):
        """Effectue une seule requête et met à jour toutes les valeurs."""
        try:
            await self._comm.connect()
            data = await self._comm.listenFrame("GET_DATAS") or {}
            await self._comm.close()
            return data
        except Exception as err:
            _LOGGER.error(f"Erreur lors de la récupération des données : {err}")
            raise UpdateFailed(f"Erreur lors de la récupération des données : {err}")
