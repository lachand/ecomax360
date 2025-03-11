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
            self.socket.setblocking(False)
            try:
                self.socket.connect((HOST, PORT))
            except socket.error as err:
                _LOGGER.error("Erreur de connexion à l'ecoMAX360 : %s", err)
                self.socket = None

    def receive(self):
        response = self.socket.recv(1024)
        return response.hex()

    def close(self):
        """Ferme la connexion TCP."""
        if self.socket:
            _LOGGER.info("Fermeture de la connexion à l'ecoMAX360")
            self.socket.close()
            self.socket = None

    def send_trame(self, trame, ack_f):
        """Envoie une trame et retourne la réponse brute."""
        ack_received = False
        max_tries = 5
        tries = 0

        if self.socket is None:
            _LOGGER.info("Reconnexion à l'ecoMAX360")
            self.connect()

        while not ack_received and tries < max_tries:
            self.scoket.sendall(trame)
            response = self.receive()
            
            if response and len(response) >= 14 and response[12:14] == ack_f:
                ack_received = True
            
            tries += 1
        _LOGGER.debug("Trame envoyée: %s, Réponse reçue: %s", trame_bytes.hex(), response)

    def request(self, trame, datastruct, dataToSearch, ack_f):
        """Construit et envoie une trame, puis traite la réponse."""
        self.connect()
        ack_received = False
        max_tries = 5
        tries = 0

        while not ack_received and tries < max_tries:
            self.socket.sendall(trame)
            asyncio.sleep(1)  # Éviter de spammer
            
            frames = self.receive()
            responses = re.findall(r'68.*?16', frames)
            
            for response in responses:
                if len(response) >= 14 and response[14:16] == ack_f:
                    if dataToSearch in response:
                        return extract_data(response, datastruct)
            tries += 1
            _LOGGER.warning("Réessai de la trame (%d/%d)", tries, max_tries)

    def extract_data(self, response, datastruct):
        """Extrait les données depuis la réponse de la chaudière."""
        values = {}
        data_bytes = bytes.fromhex(response)
        for key in datastruct:
            if datastruct[key]["type"] == int:
                values[key] = data_bytes[datastruct[key]["index"]]
            else:
                # TO FIX : Chec where it is defined as a tuple
                values[key] = extract_float(data_bytes, datastruct[key]["index"])[0]

        _LOGGER.debug("Données extraites : %s", values)
        return values
