import struct
from .parameters import PARAMETER

def float_to_hex(value):
    """Convertit un float en hexadécimal (Little Endian)."""
    float_bytes = struct.pack('<f', value)
    return float_bytes.hex()

def int_to_hex(value):
    """Convertit un entier 8 bits en hexadécimal."""
    int_bytes = struct.pack('<B', value)
    return int_bytes.hex()

def int16_to_hex(value):
    """Convertit un entier 16 bits (INT16) en hexadécimal - Little Endian."""
    int_bytes = value.to_bytes(2, byteorder='little', signed=True)
    return int_bytes.hex()

def extract_float(data, position):
    """Extrait un nombre flottant en IEEE 754 Little Endian à partir d'une position donnée"""
    return struct.unpack('<f', data[position:position+4])

def extract_data(data, dataStruct):
    values = {}
    data_bytes = bytes.fromhex(data)

    for key in dataStruct:
        if dataStruct[key]["type"] == int :
            values[key] = data_bytes[dataStruct[key]["index"]]
            if key == "MODE" :
                values[key] = dataStruct[key]["values"][data_bytes[dataStruct[key]["index"]]]
        else:
            values[key] = struct.unpack("f", data_bytes[dataStruct[key]["index"]:dataStruct[key]["index"] + 4])[0]

    print(values)

    return values

def validate_value(param, value):
    """Valide la valeur fournie pour un paramètre donné."""
    if param not in PARAMETER:
        raise ValueError("Paramètre inconnu.")

    param_info = PARAMETER[param]

    if not isinstance(value, param_info["type"]):
        raise TypeError(f"Le paramètre {param} doit être de type {param_info['type'].__name__}.")

    if not (param_info["min"] <= value <= param_info["max"]):
        raise ValueError(f"Valeur hors limites pour {param} (min: {param_info['min']}, max: {param_info['max']}).")

    return float_to_hex(value) if param_info["type"] == float else int_to_hex(value)
