"""Parameter definitions for EcoMAX controllers.

This module centralises the knowledge about the various data structures
understood by the EcoMAX controller.  Each parameter definition is a
dictionary that describes how to decode the values contained in a frame.
For example, the ``THERMOSTAT`` definition maps keys like
``"MODE"`` or ``"TEMPERATURE"`` to an index within the payload and a
Python type.  The :data:`PARAMETER` dictionary ties together high level
actions (such as ``"GET_DATAS"``) with the appropriate data structure
and search markers used to identify the frames in the incoming stream.

External consumers should import these definitions via
``from .api.parameters import THERMOSTAT, ECOMAX, PARAMETER``.
"""

from __future__ import annotations

from typing import Dict


# ---------------------------------------------------------------------------
# Data structure definitions
#
# Each data structure is a mapping of a human readable key to a dict
# specifying how to extract that value from a binary payload.  The
# ``index`` field gives the byte offset into the payload, and the ``type``
# field indicates whether to interpret the four bytes at that offset as a
# float or an int.  Some entries may include a ``values`` dictionary to
# map integer codes to human readable strings.

THERMOSTAT: Dict[str, Dict[str, object]] = {
    "MODE": {
        "index": 29,
        "type": int,
        "values": {
            0: "Auto Jour",
            1: "Nuit",
            2: "Jour",
            3: "Exterieur",
            4: "Aération",
            5: "Fête",
            6: "Vacances",
            7: "Hors-gel",
        },
    },
    "AUTO": {"index": 14, "type": int},
    "TEMPERATURE": {"index": 31, "type": float},
    "JOUR": {"index": 41, "type": float},
    "NUIT": {"index": 46, "type": float},
    "ACTUELLE": {"index": 36, "type": float},
    "HEATING": {"index": 27, "type": int},
}

# Example set code used when building frames for write operations.  A write
# operation will send this code followed by the parameter identifier and
# value.  See :class:`~custom_components.ecomax360.trame.Trame` for more
# details.
SET_CODE: str = "55 53 45 52 2d 30 30 30 00 34 30 39 35 00"

# Data structure for the main ecoMAX broadcast.  These values correspond
# to various temperatures measured by the controller.
ECOMAX: Dict[str, Dict[str, object]] = {
    "SOURCE_PRINCIPALE": {"index": 164, "type": float},
    "DEPART_RADIATEUR": {"index": 169, "type": float},
    "ECS": {"index": 179, "type": float},
    "BALLON_TAMPON": {"index": 189, "type": float},
    "TEMPERATURE_EXTERIEUR": {"index": 194, "type": float},
}

# ---------------------------------------------------------------------------
# Parameter definitions
#
# Each entry in the PARAMETER dictionary describes a high level parameter
# that can be requested from the controller.  The ``dataStruct`` field
# references one of the above data structures; ``dataToSearch`` is a
# hexadecimal marker used to identify the appropriate frames in the
# incoming stream.  Some parameters also define a ``DA`` (destination
# address) and ``SA`` (source address) which can be used when building
# explicit request frames, and a ``length`` field which is the expected
# frame length in bytes.  The ``action`` field ("GET" or "SET") may be
# used by higher level code to choose between read and write operations.

PARAMETER: Dict[str, Dict[str, object]] = {
    "GET_THERMOSTAT": {
        "action": "GET",
        "dataStruct": THERMOSTAT,
        "dataToSearch": "265535445525f78343",
        "length": 116,
    },
    "GET_DATAS": {
        "action": "GET",
        "dataStruct": ECOMAX,
        "dataToSearch": "3130303538343230303400",
        "DA": "ffff",
        "SA": "0100",
        "length": 820,
    },
}

__all__ = ["THERMOSTAT", "ECOMAX", "PARAMETER", "SET_CODE"]