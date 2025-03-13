from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

class EcomaxCoordinator(DataUpdateCoordinator):
    """Coordonne la mise à jour des capteurs en évitant les requêtes multiples."""

    def __init__(self, hass, comm):
        """Initialise le coordinateur avec une communication unique."""
        self._comm = comm
        super().__init__(
            hass,
            _LOGGER,
            name="EcomaxCoordinator",
            update_interval=timedelta(seconds=300),  # Mise à jour toutes les 30 secondes
        )

    async def _async_update_data(self):
        """Effectue une seule requête et met à jour toutes les valeurs."""
        try:
            self._comm.connect()
            data = self._comm.listenFrame("GET_DATAS") or {}
            self._comm.close()
            return data
        except Exception as err:
            raise UpdateFailed(f"Erreur lors de la récupération des données : {err}")
