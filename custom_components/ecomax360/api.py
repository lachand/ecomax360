"""API de communication avec l'ecoMAX360."""

import socket
import logging
import re
from .parameters import HOST, PORT, PARAMETER
from .trame import Trame
from .utils import extract_float

_LOGGER = logging.getLogger(__name__)

class EcoMAXAPI:
    """API pour interagir avec l'ecoMAX360 via socket TCP."""

    def __init__(self):
        """Initialisation de la connexion."""
        self.socket = None

    def connect(self):
        """Établit la connexion TCP avec la chaudière."""
        if self.socket is None:
            _LOGGER.info("Connexion à l'ecoMAX360 sur %s:%d", HOST, PORT)
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            try:
                self.socket.connect((HOST, PORT))
            except socket.error as err:
                _LOGGER.error("Erreur de connexion à l'ecoMAX360 : %s", err)
                self.socket = None

    def close(self):
        """Ferme la connexion TCP."""
        if self.socket:
            _LOGGER.info("Fermeture de la connexion à l'ecoMAX360")
            self.socket.close()
            self.socket = None

    def send_trame(self, trame: Trame):
        """Envoie une trame et retourne la réponse brute."""
        if self.socket is None:
            self.connect()
        try:
            trame_bytes = trame.build()
            self.socket.sendall(trame_bytes)
            response = self.socket.recv(1024).hex()
            _LOGGER.debug("Trame envoyée: %s, Réponse reçue: %s", trame_bytes.hex(), response)
            return response
        except socket.error as err:
            _LOGGER.error("Erreur d'envoi de la trame: %s", err)
            return None

    def request(self, dest, source, f, ack_f, param, datastruct, dataToSearch):
        """Construit et envoie une trame, puis traite la réponse."""
        self.connect()
        trame = Trame(dest, source, f, ack_f, param)
        ack_received = False
        max_tries = 3
        tries = 0

        while not ack_received and tries < max_tries:
            frames = self.send_trame(trame)
            if not frames:
                return None

            responses = re.findall(r'68.*?16', frames)
            for response in responses:
                if len(response) >= 14:
                    function = response[14:16]
                    if function == ack_f and dataToSearch in response:
                        ack_received = True
                        return self.extract_data(response, datastruct)
            tries += 1
            _LOGGER.warning("Réessai de la trame (%d/%d)", tries, max_tries)

        return None

    def extract_data(self, response, datastruct):
        """Extrait les données depuis la réponse de la chaudière."""
        values = {}
        data_bytes = bytes.fromhex(response)
        for key in datastruct:
            if datastruct[key]["type"] == int:
                values[key] = data_bytes[datastruct[key]["index"]]
            else:
                values[key] = extract_float(data_bytes, datastruct[key]["index"])

        _LOGGER.debug("Données extraites : %s", values)
        return values
