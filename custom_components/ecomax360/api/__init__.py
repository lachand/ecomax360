"""Internal API package for the EcoMAX360 integration.

This package provides the classes and structures required to talk to the
EcoMAX controller.  It exposes a single high‑level class, :class:`EcoMaxClient`,
which wraps the low‑level socket connection and provides helper methods for
receiving frames from the controller.  The individual parameter definitions
are also re‑exported here for convenience.

The API is separated into its own package so that all Home Assistant
integration code can depend on a stable interface rather than reusing the
low‑level communication primitives directly.  See :mod:`client` for the
implementation details.
"""

from .client import EcoMaxClient  # noqa: F401
from .parameters import THERMOSTAT, ECOMAX, PARAMETER  # noqa: F401

__all__ = [
    "EcoMaxClient",
    "THERMOSTAT",
    "ECOMAX",
    "PARAMETER",
]