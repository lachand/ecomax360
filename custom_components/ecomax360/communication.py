import socket
import asyncio
import logging
import re
from .parameters import PARAMETER
from .utils import extract_data

_LOGGER = logging.getLogger(__name__)

class Communication:
    def __init__(self, host: str, port: int):
        """Initialise la communication TCP avec l'ecoMAX360."""
        self.host = host
        self.port = port
        self.socket: socket.socket | None = None
        self.loop = asyncio.get_event_loop()

    async def connect(self):
        """Établit la connexion TCP si elle n'est pas déjà ouverte."""
        if self.socket is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setblocking(False)
            await self.loop.sock_connect(self.socket, (self.host, self.port))

    async def close(self):
        """Ferme la connexion TCP."""
        if self.socket:
            self.socket.close()
            self.socket = None

    async def receive(self) -> str:
        """Reçoit une trame brute et la renvoie en hexadécimal."""
        response = await self.loop.sock_recv(self.socket, 1024)
        return response.hex()

    async def request(self, trame: bytes, datastruct: dict, dataToSearch: str, ack_f: str):
        """Envoie une requête, attend une réponse contenant dataToSearch et parse les données."""
        ack_received = False
        max_tries = 3
        tries = 0

        while not ack_received and tries < max_tries:
            await self.loop.sock_sendall(self.socket, trame)
            await asyncio.sleep(1)  # éviter de spammer

            frames = await self.receive()
            responses = re.findall(r'68.*?16', frames)

            for response in responses:
                if len(response) == 116 and len(response) >= 14 and response[14:16] == ack_f:
                    if dataToSearch in response:
                        return extract_data(response, datastruct)
            tries += 1

    async def send(self, trame: bytes, ack_f: str):
        """Envoie une trame et attend un ACK."""
        _LOGGER.info("Trame envoyée : %s", trame)
        ack_received = False
        max_tries = 10
        tries = 0

        while not ack_received and tries < max_tries:
            _LOGGER.debug("Essai %s", tries)
            await self.loop.sock_sendall(self.socket, trame)
            response = await self.receive()

            if response and len(response) >= 14 and response[14:16] == ack_f:
                ack_received = True
                _LOGGER.info("Réponse reçue : %s", response)

            tries += 1

    async def listenFrame(self, param: str):
        """Écoute les trames jusqu’à trouver celle correspondant au paramètre demandé."""
        _LOGGER.info("Paramètre écouté : %s", param)
        if param not in PARAMETER:
            return None

        found = False
        tries = 0
        max_tries = 100

        while not found and tries < max_tries:
            await self.connect()
            frames = await self.receive()
            responses = re.findall(r'68.*?16', frames)

            for response in responses:
                if len(response) == 820 and PARAMETER[param]["dataToSearch"] in response:
                    return extract_data(response, PARAMETER[param]["dataStruct"])
            tries += 1
        return None
