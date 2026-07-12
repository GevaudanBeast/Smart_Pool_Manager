"""Regles de securite pour SmartPoolManager.

Fonctions pures, sans dependance Home Assistant. Ce module centralise toutes
les regles qui autorisent ou interdisent un dosage ou une filtration. La
regle fondamentale est : jamais doser si la filtration est arretee.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

WATCHDOG_MAX_S = 3600  # 1 heure max pour une pompe doseuse


def _elapsed_seconds(last: datetime) -> float:
    """Calcule le nombre de secondes ecoulees depuis last, de facon robuste.

    last peut etre naif (tests, ancien comportement) ou porteur d'un fuseau
    horaire (runtime Home Assistant, qui fournit des datetime aware). On
    compare toujours a une reference du meme type pour eviter l'erreur
    "can't subtract offset-naive and offset-aware datetimes".

    Args:
        last: instant du dernier dosage, naif ou avec fuseau.

    Returns:
        Les secondes ecoulees depuis last.
    """
    if last.tzinfo is None:
        return (datetime.now() - last).total_seconds()
    return (datetime.now(timezone.utc) - last).total_seconds()


@dataclass
class SafetyResult:
    """Resultat de l'evaluation de securite.

    Attributes:
        dosing_ok: True si le dosage est autorise.
        filtration_ok: True si la filtration est autorisee.
        reasons: liste des raisons lisibles de blocage ou d'avertissement.
        force_stop_dosing: True si une pompe doit etre coupee d'urgence.
    """

    dosing_ok: bool
    filtration_ok: bool
    reasons: list[str]
    force_stop_dosing: bool


def evaluate_safety(data: dict, config: dict) -> SafetyResult:
    """Evalue toutes les regles de securite.

    Args:
        data: dict d'etat courant (niveau, filtration, sonde, dosage en cours).
        config: dict de configuration (delai entre doses, etc.).

    Returns:
        Un SafetyResult indiquant ce qui est autorise et pourquoi.

    Regle fondamentale : jamais doser si la filtration est arretee.
    """
    reasons: list[str] = []
    dosing_ok = True
    filtration_ok = True
    force_stop = False

    # Regle 1 : niveau bas bloque tout (dosage et filtration)
    if data.get("level_low") is True:
        reasons.append("Insufficient water level")
        dosing_ok = False
        filtration_ok = False

    # Regle 2 : filtration arretee bloque le dosage (strictement)
    if not data.get("filtration_running", False):
        reasons.append("Filtration stopped - dosing forbidden")
        dosing_ok = False

    # Regle 3 : sonde indisponible bloque le dosage auto
    if data.get("ph") is None or data.get("cl") is None:
        reasons.append("Probe unavailable - auto dosing suspended")
        dosing_ok = False

    # Regle 4 : delai entre doses pH
    last_ph = data.get("last_dose_ph")
    if last_ph is not None:
        elapsed = _elapsed_seconds(last_ph)
        if elapsed < config["delay_between_doses_min"] * 60:
            reasons.append("pH dose delay not elapsed")

    # Regle 5 : delai entre doses Cl
    last_cl = data.get("last_dose_cl")
    if last_cl is not None:
        elapsed = _elapsed_seconds(last_cl)
        if elapsed < config["delay_between_doses_min"] * 60:
            reasons.append("Cl dose delay not elapsed")

    # Regle 6 : watchdog pompe (activite trop longue)
    if (
        data.get("dosing_ph_running_since_s", 0) > WATCHDOG_MAX_S
        or data.get("dosing_cl_running_since_s", 0) > WATCHDOG_MAX_S
    ):
        reasons.append("Watchdog: pump active for more than 1 hour")
        dosing_ok = False
        force_stop = True

    return SafetyResult(
        dosing_ok=dosing_ok,
        filtration_ok=filtration_ok,
        reasons=reasons,
        force_stop_dosing=force_stop,
    )
