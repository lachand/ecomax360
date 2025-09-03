"""Constants used by the EcoMAX360 integration.

This module defines a small set of constants used throughout the
integration.  Separating these values from the rest of the code makes it
easy to modify them in one place and improves the readability of the
components that rely on them.
"""

from __future__ import annotations

from homeassistant.const import Platform


# The domain string is used by Home Assistant to differentiate this
# integration from others.  It must match the name of the directory in
# ``custom_components``.
DOMAIN: str = "ecomax360"

# Configuration keys exposed to the user via the config flow.  These
# constants are used to avoid hard coding strings throughout the code.
CONF_HOST: str = "host"
CONF_PORT: str = "port"
CONF_SCAN_INTERVAL: str = "scan_interval"

# Default polling interval (in seconds) for the DataUpdateCoordinator.  The
# user may override this value via the options flow; this default is used
# when no override is provided.
DEFAULT_SCAN_INTERVAL: int = 30

# Platforms that the integration supports.  When adding new platform
# modules (e.g. a binary sensor or water heater), append them here and
# update the ``PLATFORMS`` list in the root ``__init__`` accordingly.
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CLIMATE]