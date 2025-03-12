import socket
import asyncio
import logging
import re
from .parameters import HOST, PORT, PARAMETER
from .utils import extract_data

_LOGGER = logging.getLogger(__name__)

class Communication:
    def __init__(self):
        self.socket = None
        self.loop = asyncio.get_event_loop()

    async def connect(self):
        if self.socket is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setblocking(False)
            await self.loop.sock_connect(self.socket, (HOST, PORT))

    async def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None

    async def receive(self):
        response = await self.loop.sock_recv(self.socket, 1024)
        return response.hex()

    async def request(self, trame, datastruct, dataToSearch, ack_f):
        ack_received = False
        max_tries = 3
        tries = 0

        while not ack_received and tries < max_tries:
            await self.loop.sock_sendall(self.socket, trame)
            await asyncio.sleep(1)  # Éviter de spammer
            
            frames = await self.receive()
            responses = re.findall(r'68.*?16', frames)
            
            for response in responses:
                if len(response) >= 14 and response[14:16] == ack_f:
                    if dataToSearch in response:
                        _LOGGER.info("Taille de trame :")
                        _LOGGER.info(len(response))
                        return extract_data(response, datastruct)
            tries += 1

    async def send(self, trame, ack_f):
        _LOGGER.info(trame)
        ack_received = False
        max_tries = 5
        tries = 0

        while not ack_received and tries < max_tries:
            await self.loop.sock_sendall(self.socket, trame)
            response = await self.receive()
            
            if response and len(response) >= 14 and response[12:14] == ack_f:
                ack_received = True
            
            tries += 1

    async def listenFrame(self, param):
        if param not in PARAMETER:
            return None

        await self.connect()
        frames = await self.receive()
        responses = re.findall(r'68.*?16', frames)

        for response in responses:
            if PARAMETER[param]["dataToSearch"] in response:
                return extract_data(response, PARAMETER[param]["dataStruct"])
        return None
