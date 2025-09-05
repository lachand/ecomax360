"""API de communication avec l'ecoMAX360."""

import socket
import logging
import re
import struct
from .parameters import PARAMETER, THERMOSTAT
from .trame import Trame
from .utils import extract_float
from .communication import Communication

_LOGGER = logging.getLogger(__name__)

class EcoMAXAPI:
    """API pour interagir avec l'ecoMAX360 via socket TCP."""

    def __init__(self, host: str, port: int):
        """Initialisation de la connexion."""
        self.host = host
        self.port = port
        self.socket: socket.socket | None = None

    # -------------------- Gestion connexion --------------------

    def connect(self) -> None:
        """Ouvre une connexion TCP si nécessaire."""
        if self.socket is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            _LOGGER.debug("Connexion à %s:%s …", self.host, self.port)
            self.socket.connect((self.host, self.port))
            _LOGGER.debug("Connecté à %s:%s", self.host, self.port)

    def close(self) -> None:
        """Ferme la connexion TCP."""
        if self.socket:
            try:
                self.socket.close()
            finally:
                self.socket = None

    # -------------------- I/O bas niveau --------------------

    def _send(self, payload: bytes) -> None:
        """Envoie des octets sur la socket."""
        if not self.socket:
            raise RuntimeError("Socket non connectée")
        self.socket.sendall(payload)

    def _recv_hex(self, bufsize: int = 2048) -> str:
        """Reçoit des octets et renvoie la trame en hex (sans espaces)."""
        if not self.socket:
            raise RuntimeError("Socket non connectée")
        data = self.socket.recv(bufsize)
        return data.hex()

    # -------------------- Opérations haut niveau --------------------

    def request(self, trame: Trame, datastruct: dict, data_to_search: str, ack_flag: str | None = None):
        """
        Envoie une trame et attend une réponse contenant `data_to_search`.
        Si `ack_flag` est fourni, on vérifie le flag d'ACK (aux positions 14:16 en hex).
        Retourne un dict de valeurs parsées selon `datastruct`, sinon None.
        """
        self.connect()

        tries = 0
        max_tries = 3
        while tries < max_tries:
            payload = trame.to_bytes() if hasattr(trame, "to_bytes") else bytes(trame)  # tolérant
            _LOGGER.debug("Envoi trame (%d octets)", len(payload))
            self._send(payload)

            # petite pause (certaines cartes ont besoin d’un temps de latence)
            # -> si tu as du non-bloquant ailleurs, adapte avec asyncio.sleep là-bas
            # ici on reste synchrone pour rester compatible avec le code existant
            try:
                frames = self._recv_hex(4096)
            except socket.timeout:
                tries += 1
                continue

            # on découpe toutes les réponses possibles 68 ... 16
            responses = re.findall(r'68.*?16', frames)
            for response in responses:
                if ack_flag is not None and (len(response) < 16 or response[14:16] != ack_flag):
                    continue
                if data_to_search in response:
                    return self.extract_data(response, datastruct)

            tries += 1

        _LOGGER.warning("Aucune réponse valide après %d tentatives", max_tries)
        return None

    def listen_frame(self, param: str):
        """
        Écoute en boucle jusqu’à trouver la frame correspondant au paramètre `param`
        (doit exister dans PARAMETER). Retourne le dict parsé ou None.
        """
        if param not in PARAMETER:
            _LOGGER.error("Paramètre inconnu: %s", param)
            return None

        self.connect()

        tries = 0
        max_tries = 100
        data_to_search = PARAMETER[param]["dataToSearch"]

        while tries < max_tries:
            try:
                frames = self._recv_hex(4096)
            except socket.timeout:
                tries += 1
                continue

            responses = re.findall(r'68.*?16', frames)
            for response in responses:
                # logique héritée : frame attendue de longueur 820 en hex
                if len(response) == 820 and data_to_search in response:
                    return self.extract_data(response, PARAMETER[param]["dataStruct"])
            tries += 1

        _LOGGER.warning("Frame %s introuvable après %d essais", param, max_tries)
        return None

    # -------------------- Parsing --------------------

    def extract_data(self, response: str, datastruct: dict) -> dict:
        """Extrait les données depuis la réponse de la chaudière."""
        values: dict = {}
        data_bytes = bytes.fromhex(response)
        for key, spec in datastruct.items():
            if spec["type"] == int:
                values[key] = data_bytes[spec["index"]]
            else:
                # TODO: gérer proprement les tuples si utilisés dans datastruct
                values[key] = extract_float(data_bytes, spec["index"])[0]

        _LOGGER.debug("Données extraites : %s", values)
        return values

    # ------------------------- helpers bas niveau -------------------------
    def _float_to_hex(self, value: float) -> str:
        try:
            return struct.pack("<f", value).hex()
        except Exception:  # pragma: no cover
            return struct.pack("<f", 0.0).hex()

    # ------------------------- méthodes haut-niveau -----------------------
    async def async_change_preset(self, preset_hex: str) -> None:
        """Change le mode (preset)."""
        frame = Trame("6400", "0100", "29", "a9", "011e01", preset_hex).build()
        comm = Communication(self.host, self.port)
        await comm.connect()
        await comm.send(frame, "a9")
        await comm.close()

    async def async_set_setpoint(self, code: str, temperature: float) -> None:
        """Applique une consigne de température avec le registre donné."""
        frame = Trame(
            "6400", "0100", "29", "a9", code, self._float_to_hex(temperature)
        ).build()
        comm = Communication(self.host, self.port)
        await comm.connect()
        await comm.send(frame, "a9")
        await comm.close()

    async def async_get_thermostat(self) -> dict | None:
        """Retourne l'état du thermostat (dictionnaire)."""
        frame = Trame("64 00", "20 00", "40", "c0", "647800", "").build()
        comm = Communication(self.host, self.port)
        await comm.connect()
        data = await comm.request(frame, THERMOSTAT, "265535445525f78343", "c0")
        await comm.close()
        return data

    # ------------------------- méthodes avancées --------------------------
    async def async_set_auto(self, enable: bool) -> None:
        """Active/désactive le mode AUTO thermostat.
        
        Implémentation : certains firmwares acceptent un registre dédié.
        Si votre protocole exige une autre trame, adaptez ici sans toucher
        aux entités.
        """
        # Exemple : bit AUTO dans le registre 0x011e02 (à ajuster si nécessaire)
        reg = "011e02"
        payload = "01" if enable else "00"
        frame = Trame("6400", "0100", "29", "a9", reg, payload).build()
        comm = Communication(self.host, self.port)
        await comm.connect()
        await comm.send(frame, "a9")
        await comm.close()

    async def async_set_dhw_setpoint(self, temperature: float) -> None:
        """Modifie la consigne ECS (exemple). Ajustez le registre selon votre doc."""
        # Exemple : registre hypothétique 0x013001 pour ECS
        frame = Trame(
            "6400", "0100", "29", "a9", "013001", self._float_to_hex(temperature)
        ).build()
        comm = Communication(self.host, self.port)
        await comm.connect()
        await comm.send(frame, "a9")
        await comm.close()

    async def async_get(self, key: str) -> dict | None:
        """Helper générique GET basé sur `PARAMETER[key]` si défini.

        Permet de réutiliser la table `PARAMETER` sans exposer la construction
        de trames à l’extérieur. Exemple : `await api.async_get("GET_DATAS")`.
        """
        if key not in PARAMETER:
            _LOGGER.error("PARAMETER[%s] introuvable", key)
            return None
        p = PARAMETER[key]
        frame = Trame("64 00", "20 00", "40", "c0", p["payload"], "").build()
        comm = Communication(self.host, self.port)
        await comm.connect()
        data = await comm.request(frame, p["dataStruct"], p["dataToSearch"], "c0")
        await comm.close()
        return data

