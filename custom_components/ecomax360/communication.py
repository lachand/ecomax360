import socket
from .parameters import HOST, PORT, PARAMETER
from .utils import extract_data
import re

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

    def listenFrame(self, param):
        """Écoute une trame et retourne les valeurs pour chaque capteur."""
        if param not in PARAMETER:
            return None

        self.connect()
        frames = self.socket.recv(1024).hex()
        responses = re.findall(r'68.*?16', frames)

        for response in responses:
            if PARAMETER[param]["dataToSearch"] in response:
                return extract_data(response, PARAMETER[param]["dataStruct"])
        return None
