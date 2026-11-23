"""Filtre de plausibilite des mesures de sonde pour SmartPoolManager.

Fonctions pures, sans dependance Home Assistant. Une sonde peut publier des
valeurs numeriques sentinelles (9999, -0.1, pH 2.1 hors de l'eau) que
safe_float accepte. Ce module ecarte toute mesure hors d'une plage physique
plausible : elle est traitee comme indisponible, et sa valeur brute est
conservee pour le diagnostic.
"""

from __future__ import annotations

# Plages plausibles (bornes incluses) pour une piscine en service.
# Hors plage, la mesure est consideree comme un defaut de sonde.
PLAUSIBLE_RANGES: dict[str, tuple[float, float]] = {
    "ph": (5.0, 9.5),
    "orp": (0.0, 1200.0),  # mV
    "cl": (0.0, 10.0),  # mg/L chlore libre
    "tds": (0.0, 9000.0),  # ppm
    "salinity": (0.0, 50.0),  # g/L
    "water_temperature": (-5.0, 45.0),  # degres C
}


def sanitize_measures(raw: dict) -> tuple[dict, dict[str, float]]:
    """Remplace par None les mesures hors plage plausible.

    Args:
        raw: dict des lectures brutes (valeurs float ou None). Les cles absentes
            de PLAUSIBLE_RANGES sont recopiees telles quelles.

    Returns:
        Un tuple (clean, rejected). clean est une copie de raw ou chaque
        mesure hors plage vaut None. rejected associe le nom de chaque mesure
        rejetee a sa valeur brute. raw n'est pas modifie.
    """
    clean = dict(raw)
    rejected: dict[str, float] = {}
    for key, (low, high) in PLAUSIBLE_RANGES.items():
        value = clean.get(key)
        if value is None:
            continue
        if not low <= value <= high:
            rejected[key] = value
            clean[key] = None
    return clean, rejected
