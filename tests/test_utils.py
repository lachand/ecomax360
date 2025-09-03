"""Tests for utility functions used in the EcoMAX360 integration."""

import struct

from custom_components.ecomax360.utils import (
    float_to_hex,
    int_to_hex,
    int16_to_hex,
    extract_float,
    extract_data,
)
from custom_components.ecomax360.api.parameters import THERMOSTAT, ECOMAX


def test_numeric_conversions() -> None:
    """Verify that numeric conversion helpers produce the correct hex strings."""
    assert float_to_hex(1.0) == struct.pack("<f", 1.0).hex()
    assert int_to_hex(255) == struct.pack("<B", 255).hex()
    # int16_to_hex returns little endian signed 16 bit
    assert int16_to_hex(256) == (256).to_bytes(2, byteorder="little", signed=True).hex()


def test_extract_float() -> None:
    """Verify that extract_float correctly decodes IEEE 754 floats from raw bytes."""
    value = 23.45
    b = struct.pack("<f", value)
    data = b + b  # duplicate to test offset
    result, = extract_float(data, 0)
    assert abs(result - value) < 1e-6
    result2, = extract_float(data, 4)
    assert abs(result2 - value) < 1e-6


def test_extract_data_thermostat() -> None:
    """Test extract_data with a synthetic thermostat frame."""
    # Build a payload with known values at the correct offsets
    payload = bytearray(60)
    # MODE (int at index 29)
    payload[29] = 2  # comfort
    # AUTO (int at index 14)
    payload[14] = 1
    # TEMPERATURE (float at index 31)
    temp = 65.5
    payload[31:35] = struct.pack("<f", temp)
    # JOUR (float at index 41)
    payload[41:45] = struct.pack("<f", 21.0)
    # NUIT (float at index 46)
    payload[46:50] = struct.pack("<f", 19.0)
    # ACTUELLE (float at index 36)
    payload[36:40] = struct.pack("<f", 23.0)
    # HEATING (int at index 27)
    payload[27] = 1
    # Convert to hex string
    data_hex = payload.hex()
    values = extract_data(data_hex, THERMOSTAT)
    assert values["MODE"] == 2
    assert values["AUTO"] == 1
    assert abs(values["TEMPERATURE"] - 65.5) < 1e-6
    assert abs(values["JOUR"] - 21.0) < 1e-6
    assert abs(values["NUIT"] - 19.0) < 1e-6
    assert abs(values["ACTUELLE"] - 23.0) < 1e-6
    assert values["HEATING"] == 1


def test_extract_data_ecomax() -> None:
    """Test extract_data with a synthetic EcoMAX data frame."""
    payload = bytearray(200)
    payload[164:168] = struct.pack("<f", 60.0)  # SOURCE_PRINCIPALE
    payload[169:173] = struct.pack("<f", 55.0)  # DEPART_RADIATEUR
    payload[179:183] = struct.pack("<f", 50.0)  # ECS
    payload[189:193] = struct.pack("<f", 30.0)  # BALLON_TAMPON
    payload[194:198] = struct.pack("<f", 15.0)  # TEMPERATURE_EXTERIEUR
    values = extract_data(payload.hex(), ECOMAX)
    assert abs(values["SOURCE_PRINCIPALE"] - 60.0) < 1e-6
    assert abs(values["DEPART_RADIATEUR"] - 55.0) < 1e-6
    assert abs(values["ECS"] - 50.0) < 1e-6
    assert abs(values["BALLON_TAMPON"] - 30.0) < 1e-6
    assert abs(values["TEMPERATURE_EXTERIEUR"] - 15.0) < 1e-6