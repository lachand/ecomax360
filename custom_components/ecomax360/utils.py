"""Common helper functions for the EcoMAX360 integration.

This module provides a set of utility functions used throughout the
integration for converting between numeric types and hexadecimal
representations, and for extracting values from the binary payloads
returned by the EcoMAX controller.  All functions are documented
below and include type annotations for clarity.
"""

from __future__ import annotations

import struct
from typing import Dict, Tuple, Any, Sequence

from .api.parameters import PARAMETER


def float_to_hex(value: float) -> str:
    """Convert a Python float to a hexadecimal string.

    The float is encoded using little‑endian IEEE‑754 format.  The
    returned string contains exactly eight hexadecimal characters (four
    bytes) without any prefix.  This helper is primarily used when
    constructing write commands for the EcoMAX controller.

    Parameters
    ----------
    value: float
        The floating point number to encode.

    Returns
    -------
    str
        The little‑endian hexadecimal representation of ``value``.
    """
    float_bytes = struct.pack("<f", value)
    return float_bytes.hex()


def int_to_hex(value: int) -> str:
    """Convert an 8‑bit integer to a two‑character hexadecimal string.

    Parameters
    ----------
    value: int
        An integer in the range 0–255.

    Returns
    -------
    str
        A two‑character hexadecimal representation of ``value``.
    """
    int_bytes = struct.pack("<B", value)
    return int_bytes.hex()


def int16_to_hex(value: int) -> str:
    """Convert a 16‑bit integer to a four‑character little‑endian hex string.

    The returned string contains exactly four hexadecimal characters.  It
    encodes ``value`` in little‑endian byte order, signed.  This helper
    is used by :class:`Trame` to compute the frame length field.

    Parameters
    ----------
    value: int
        The integer to convert (may be signed).

    Returns
    -------
    str
        The little‑endian hexadecimal representation of ``value``.
    """
    int_bytes = value.to_bytes(2, byteorder="little", signed=True)
    return int_bytes.hex()


def extract_float(data: bytes, position: int) -> Tuple[float]:
    """Extract a 32‑bit little‑endian float from a byte sequence.

    Parameters
    ----------
    data: bytes
        The buffer from which to extract the float.
    position: int
        The starting index within ``data`` at which to unpack four
        bytes.  The function does not perform bounds checking; callers
        should ensure the buffer is large enough.

    Returns
    -------
    tuple(float)
        A one‑element tuple containing the decoded float.  This
        matches the return value of :func:`struct.unpack`.
    """
    return struct.unpack("<f", data[position : position + 4])


def extract_data(data: str, data_struct: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Decode a payload according to a data structure definition.

    This helper interprets the hexadecimal payload returned by the
    controller according to a mapping of keys to extraction rules.  The
    rules specify the byte index and the type (``int`` or ``float``)
    expected at that position.  Floats are decoded using little‑endian
    IEEE‑754 representation.  Integer values are returned as plain
    integers.  Additional mappings (``values``) defined in the
    structure are not applied here; callers may perform such mapping
    themselves.

    Parameters
    ----------
    data: str
        A string of hexadecimal characters representing the payload.
    data_struct: dict
        The structure definition.  Each key maps to a dictionary with
        at least ``"index"`` (byte offset) and ``"type"`` (``int`` or
        ``float``).  Optionally, a ``"values"`` mapping may be present
        but is ignored by this function.

    Returns
    -------
    dict
        A mapping from keys to decoded numeric values.
    """
    values: Dict[str, Any] = {}
    data_bytes = bytes.fromhex(data)
    for key, spec in data_struct.items():
        idx = spec.get("index")
        typ = spec.get("type")
        if idx is None or typ is None:
            continue
        if typ is int:
            values[key] = data_bytes[idx]
        else:
            # Unpack a float from the four bytes starting at idx
            values[key] = struct.unpack("<f", data_bytes[idx : idx + 4])[0]
    return values


def validate_value(param: str, value: Any) -> str:
    """Validate and encode a value for a given parameter.

    Given a parameter name and a value, this function checks that the
    parameter exists in the :data:`PARAMETER` definitions, verifies
    that the value is of the correct type and within the allowed range
    (based on ``min`` and ``max`` keys), and finally encodes it as a
    hexadecimal string.  This helper can be used when constructing
    write commands to ensure user input is valid before sending it to
    the controller.

    Parameters
    ----------
    param: str
        The parameter key to validate.
    value: Any
        The value supplied by the user.  Its type and range must
        conform to the specification in :data:`PARAMETER[param]`.

    Returns
    -------
    str
        The encoded hexadecimal value, either two characters for
        integers or eight characters for floats.

    Raises
    ------
    ValueError
        If ``param`` is unknown or the value is out of range.
    TypeError
        If the value is not of the expected type.
    """
    if param not in PARAMETER:
        raise ValueError("Unknown parameter.")
    param_info = PARAMETER[param]
    expected_type = param_info.get("type")
    if expected_type is not None and not isinstance(value, expected_type):
        raise TypeError(
            f"Parameter {param} must be of type {expected_type.__name__}, got {type(value).__name__}."
        )
    minimum = param_info.get("min")
    maximum = param_info.get("max")
    if minimum is not None and maximum is not None:
        if not (minimum <= value <= maximum):
            raise ValueError(
                f"Value out of range for {param} (min: {minimum}, max: {maximum})."
            )
    # Encode according to the type
    if expected_type is float:
        return float_to_hex(float(value))
    elif expected_type is int:
        return int_to_hex(int(value))
    else:
        # Fallback for untyped values: return str directly
        return str(value)
