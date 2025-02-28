"""Utilitaires pour les conversions et manipulations de données ecoMAX360."""

import struct

def int16_to_hex(value):
    """Convertit un entier 16 bits en une chaîne hexadécimale formatée."""
    return "{:04x}".format(value)

def extract_float(data_bytes, index):
    """Extrait une valeur float à partir d'un tableau d'octets."""
    return struct.unpack('<f', data_bytes[index:index+4])[0]
