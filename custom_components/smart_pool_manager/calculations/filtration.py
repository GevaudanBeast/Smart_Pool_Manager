"""Calculs de duree de filtration pour SmartPoolManager.

Fonctions pures, sans dependance Home Assistant. La regle de base est
"temperature divisee par deux en heures", etendue avec des marges de
securite pour fournir une fourchette min / recommande / max exploitable
par Solar Optimizer.
"""

from __future__ import annotations

import math


def calculate_filtration_duration(temperature: float) -> dict:
    """Calcule les durees de filtration recommandees selon la temperature.

    Args:
        temperature: temperature de l'eau en degres Celsius.

    Returns:
        Un dict avec les cles recommended, min et max exprimees en minutes.

    La regle suit une approche par paliers de temperature. Plus l'eau est
    chaude, plus la filtration doit etre longue pour limiter le developpement
    des algues et des bacteries.
    """
    if temperature < 12:
        return {"recommended": 120, "min": 60, "max": 180}
    elif temperature < 16:
        return {"recommended": 240, "min": 180, "max": 300}
    elif temperature < 20:
        return {"recommended": 360, "min": 240, "max": 480}
    elif temperature < 24:
        return {"recommended": 480, "min": 360, "max": 600}
    elif temperature < 28:
        return {"recommended": 600, "min": 480, "max": 720}
    else:
        return {"recommended": 720, "min": 600, "max": 840}


def adjust_for_dosing(durations: dict, dosing_total_s: int) -> dict:
    """Etend la duree min si un dosage planifie depasse la filtration.

    On ne doit jamais doser sans filtration active. Si la duree totale de
    dosage prevue est superieure a la duree min de filtration, on allonge
    cette derniere pour couvrir le dosage plus un tampon de 30 minutes.

    Args:
        durations: dict issu de calculate_filtration_duration.
        dosing_total_s: duree totale de dosage planifiee, en secondes.

    Returns:
        Le dict durations potentiellement ajuste (modifie sur place et
        renvoye pour faciliter le chainage).
    """
    required_s = dosing_total_s + 1800  # 30 min de tampon
    required_min = math.ceil(required_s / 60)
    if required_min > durations["min"]:
        durations["min"] = required_min
        durations["recommended"] = max(durations["recommended"], required_min)
    return durations
