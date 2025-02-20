HOST = "192.168.1.37"
PORT = 8899

THERMOSTAT = {
    "MODE": {"index": 29, "type": int},
    "AUTO": {"index": 14, "type": int},
    "TEMPERATURE": {"index": 31, "type": float},
    "JOUR": {"index": 41, "type": float},
    "NUIT": {"index": 46, "type": float},
    "ACTUELLE": {"index": 36, "type": float}
}

ECOMAX = {
    "SOURCE_PRINCIPALE": {"index": 164, "type": float},
    "DEPART_RADIATEUR": {"index": 169, "type": float},
    "ECS": {"index": 179, "type": float},
    "BALLON_TAMPON": {"index": 189, "type": float},
    "TEMPERATURE_EXTERIEUR": {"index": 194, "type": float}
}

PARAMETER = {
    "GET_THERMOSTAT": {"action": "GET", "dataStruct": THERMOSTAT, "dataToSearch": "265535445525f78343", "length": 116},
    "GET_DATAS": {"action": "GET", "dataStruct": ECOMAX, "dataToSearch": "3130303538343230303400", "DA": "ffff", "SA": "0100"}
}
