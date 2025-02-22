import socket
from .parameters import HOST, PORT, PARAMETER
from .utils import extract_data
import re
import logging
import time
_LOGGER = logging.getLogger(__name__)

class Communication:
    def __init__(self):
        self.socket = None

    def connect(self):
        if self.socket is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((HOST, PORT))

    def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None

    def receive(self):
        response = self.socket.recv(1024)
        return response.hex()

    def request(self, trame, datastruct, dataToSearch, ack_f):
        """
                Envoie une trame et attend un ACK en réponse.
                Si aucun ACK n'est reçu, la trame est renvoyée toutes les secondes.
                """
        ack_received = False
        da_sent = trame[4:8]  # DA envoyé
        sa_sent = trame[8:12]  # SA envoyé

        max_tries = 10
        tries = 0

        while not ack_received and tries < max_tries:
            self.socket.sendall(trame)

            frames = self.socket.recv(1024).hex()
            responses = re.findall(r'68.*?16', frames)

            for response in responses:
                if len(response) >= 14:  # Vérification d'une taille minimale
                    # da_received = response[8:12]  # DA reçu
                    # sa_received = response[4:8]  # SA reçu
                    function = response[14:16]  # Code fonction

                    # Vérification du SA et DA dans la réponse
                    if function == ack_f and len(response) == 116:  # On vérifie que la réponse correspond bien à l'ack. and da_received == sa_sent and sa_received == da_sent:
                        ack_received = True
                        if dataToSearch in response:  # and len(response) == 116:
                            datas = extract_data(response, datastruct)
                            return datas
            else:
                tries = tries + 1

    def send(self, trame, ack_f):
        """
        Envoie une trame et attend un ACK en réponse.
        Si aucun ACK n'est reçu, la trame est renvoyée toutes les secondes.
        """
        ack_received = False
        da_sent = trame[4:8]  # DA envoyé
        sa_sent = trame[8:12]  # SA envoyé
        tries = 0
        max_tries = 15

        while not ack_received and tries < max_tries:
            self.socket.sendall(trame)
            response = self.receive()
            
            _LOGGER.info(trame)

            if response:
                if len(response) >= 14:  # Vérification d'une taille minimale
                    #da_received = response[8:12]  # DA reçu
                    #sa_received = response[4:8]  # SA reçu
                    function = response[12:14]  # Code fonction

                    # Vérification du SA et DA dans la réponse
                    if function == ack_f: # On vérifie que la réponse correspond bien à l'ack. and da_received == sa_sent and sa_received == da_sent:
                        ack_received = True
            tries = tries + 1

    def listenFrame(self, param):
        """Écoute une trame et retourne les valeurs pour chaque capteur."""
        message = f"Requête envoyée : {param}"
        logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        if param not in PARAMETER:
            return None

        self.connect()
        frames = self.socket.recv(1024).hex()
        responses = re.findall(r'68.*?16', frames)

        for response in responses:
            if PARAMETER[param]["dataToSearch"] in response:
                return extract_data(response, PARAMETER[param]["dataStruct"])
        return None
