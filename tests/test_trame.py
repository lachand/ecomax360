"""Tests for the frame construction utilities (Trame).

This module contains unit tests to verify that the :class:`~custom_components.ecomax360.trame.Trame`
class correctly computes frame lengths and CRC checksums according to the
EcoMAX protocol.  The tests do not require a live controller; they
validate the integrity of frames built locally.
"""

from pathlib import Path
import importlib.util


def _load_trame_module():
    """Dynamically load the Trame module and its dependencies.

    The module ``custom_components.ecomax360.trame`` uses relative imports
    (e.g. ``from .utils import int16_to_hex``), which require a proper
    package structure in ``sys.modules``.  To avoid importing
    Home Assistant during testing, this helper constructs the minimal
    package hierarchy needed to satisfy those relative imports.

    It loads ``utils.py`` and ``api/parameters.py`` from the integration
    directory and registers them under the names
    ``custom_components.ecomax360.utils`` and
    ``custom_components.ecomax360.api.parameters`` respectively.  It
    then loads ``trame.py`` with its ``__package__`` set to
    ``custom_components.ecomax360`` so that the relative imports are
    resolved against these preloaded modules.

    Returns
    -------
    module
        The loaded ``trame`` module.
    """
    import sys
    base = Path(__file__).resolve().parents[1]
    cc_dir = base / "custom_components" / "ecomax360"
    # Helper to load a module from file and register it in sys.modules
    def load_module(name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)  # type: ignore[assignment]
        sys.modules[name] = module
        return module
    # Ensure package hierarchy exists
    if 'custom_components' not in sys.modules:
        pkg = importlib.util.module_from_spec(importlib.machinery.ModuleSpec('custom_components', None))
        sys.modules['custom_components'] = pkg
    if 'custom_components.ecomax360' not in sys.modules:
        sub_pkg = importlib.util.module_from_spec(
            importlib.machinery.ModuleSpec('custom_components.ecomax360', None, is_package=True)
        )
        sys.modules['custom_components.ecomax360'] = sub_pkg
    # Load utils and api.parameters modules into sys.modules so relative imports work
    load_module('custom_components.ecomax360.utils', cc_dir / 'utils.py')
    api_dir = cc_dir / 'api'
    load_module('custom_components.ecomax360.api.parameters', api_dir / 'parameters.py')
    # Now load trame with correct package
    trame_path = cc_dir / 'trame.py'
    spec_trame = importlib.util.spec_from_file_location(
        'custom_components.ecomax360.trame', trame_path
    )
    trame_module = importlib.util.module_from_spec(spec_trame)
    # Set the package so that relative imports (from .utils) resolve correctly
    trame_module.__package__ = 'custom_components.ecomax360'
    assert spec_trame.loader is not None
    spec_trame.loader.exec_module(trame_module)  # type: ignore[assignment]
    # Register the loaded module
    sys.modules['custom_components.ecomax360.trame'] = trame_module
    return trame_module


def test_trame_crc_and_length() -> None:
    """Verify that the CRC and length computed for a simple frame are correct.

    A frame is constructed using known parameters.  The resulting
    binary representation is examined to ensure that the start (0x68)
    and end (0x16) markers are present, the length bytes reflect the
    expected payload size and the CRC matches a recomputation using
    :meth:`Trame.calculate_crc`.
    """
    trame_mod = _load_trame_module()
    Trame = trame_mod.Trame
    trame = Trame("6400", "0100", "29", "a9", "011e01", "00")
    frame = trame.build()
    # The first and last bytes must be 0x68 and 0x16
    assert frame[0] == 0x68
    assert frame[-1] == 0x16
    # CRC occupies the two bytes before the end byte
    crc_in_frame = frame[-3:-1]
    # Recompute CRC over everything between L0 and the end of data
    crc_calc = trame_mod.Trame.calculate_crc(frame[1:-3])
    assert crc_in_frame == crc_calc
    # Decode the length from the frame (little endian)
    length_from_frame = frame[2] << 8 | frame[1]
    expected_length = int(trame.l1, 16) << 8 | int(trame.l0, 16)
    assert length_from_frame == expected_length