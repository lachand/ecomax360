"""Mappages EcoMAX ↔ Home Assistant.

Séparer ces conversions permet d’alléger les entités et de réutiliser
les correspondances ailleurs (tests, autres plateformes, UI, etc.).
"""
from homeassistant.components.climate.const import (
  PRESET_AWAY,
  PRESET_COMFORT,
  PRESET_ECO,
)

# Codes de mode renvoyés par l’ecoMAX (entiers) → presets Home Assistant
EM_TO_HA_MODES: dict[int, str] = {
    0: "Calendrier",   # Auto Jour (ton libellé d’origine)
    1: PRESET_ECO,     # Nuit
    2: PRESET_COMFORT, # Jour
    3: "Exterieur",
    4: "Aeration",
    5: "Fete",
    6: "Vacances",
    7: PRESET_AWAY,    # Hors-gel
}

# Presets Home Assistant → codes hex envoyés à l’ecoMAX
HA_TO_EM_MODES: dict[str, str] = {
    "Calendrier": "03",
    PRESET_ECO: "02",
    PRESET_COMFORT: "01",
    "Exterieur": "07",
    "Aeration": "04",
    "Fete": "05",
    "Vacances": "06",
    PRESET_AWAY: "00",
}

def em_to_ha(mode_code: int, default: str = "Calendrier") -> str:
  """Convertit un code mode ecoMAX (int) en preset HA, avec défaut sûr."""
  return EM_TO_HA_MODES.get(mode_code, default)

def ha_to_em(preset: str, default: str = "00") -> str:
  """Convertit un preset HA en code hex ecoMAX, avec défaut sûr."""
  return HA_TO_EM_MODES.get(preset, default)
