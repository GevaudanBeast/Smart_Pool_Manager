"""Calculs chimiques pour SmartPoolManager.

Fonctions pures de calcul des doses (pH-, desinfectant) et d'evaluation des
statuts chimiques. Aucune dependance Home Assistant. Les formules sont
volontairement simples et lineaires : elles fournissent une estimation
prudente, plafonnee par une dose maximale configurable.
"""

from __future__ import annotations


def calculate_ph_dose(
    ph_measured: float,
    ph_target: float,
    ph_tolerance: float,
    volume_m3: float,
    concentration_pct: float,
    dose_max_ml: float,
) -> float:
    """Calcule le volume de pH- a injecter en mL.

    Retourne 0.0 si le pH est dans la tolerance ou en dessous de la cible
    (on ne baisse pas un pH deja correct ou trop bas).

    Formule : volume_L * delta_pH * facteur_concentration.
    Le facteur de base 0.18 correspond a de l'acide chlorhydrique a 14 pour
    cent. Il est ajuste lineairement selon la concentration reelle du produit.
    """
    if ph_measured <= (ph_target + ph_tolerance):
        return 0.0
    delta = ph_measured - ph_target
    factor = 0.18 * (14.0 / concentration_pct)
    dose = volume_m3 * 1000.0 * delta * factor
    return round(min(dose, dose_max_ml), 1)


def calculate_cl_dose(
    cl_measured: float,
    cl_target: float,
    cl_tolerance: float,
    volume_m3: float,
    concentration_pct: float,
    dose_max_ml: float,
) -> float:
    """Calcule le volume de desinfectant a injecter en mL.

    Retourne 0.0 si le Cl est dans la tolerance ou au dessus de la cible.

    Le facteur de base 0.025 correspond a de l'hypochlorite de sodium a 14
    pour cent de chlore actif. Il est ajuste selon la concentration reelle.
    """
    if cl_measured >= (cl_target - cl_tolerance):
        return 0.0
    delta = cl_target - cl_measured
    factor = 0.025 * (14.0 / concentration_pct)
    dose = volume_m3 * 1000.0 * delta * factor
    return round(min(dose, dose_max_ml), 1)


def calculate_dose_duration_s(dose_ml: float, flow_rate_ml_min: float) -> int:
    """Convertit un volume de dose en duree de pompage en secondes.

    Retourne 0 si la dose est nulle ou si le debit est invalide (evite une
    division par zero).
    """
    if dose_ml <= 0.0 or flow_rate_ml_min <= 0.0:
        return 0
    return int((dose_ml / flow_rate_ml_min) * 60)


def evaluate_ph_status(
    ph: float | None,
    ph_target: float,
    ph_tolerance: float,
) -> str:
    """Evalue le statut du pH : OK, HIGH, LOW, CRITICAL ou UNKNOWN."""
    if ph is None:
        return "UNKNOWN"
    if abs(ph - ph_target) <= ph_tolerance:
        return "OK"
    if ph > ph_target + ph_tolerance:
        return "HIGH" if ph < 8.0 else "CRITICAL"
    return "LOW" if ph > 6.5 else "CRITICAL"


def evaluate_cl_status(
    cl: float | None,
    cl_target: float,
    cl_tolerance: float,
) -> str:
    """Evalue le statut du Cl : OK, HIGH, LOW ou UNKNOWN."""
    if cl is None:
        return "UNKNOWN"
    if abs(cl - cl_target) <= cl_tolerance:
        return "OK"
    return "HIGH" if cl > cl_target + cl_tolerance else "LOW"


def evaluate_orp_status(orp: float | None, orp_min: float) -> str:
    """Evalue le statut de l'ORP : OK, LOW, CRITICAL ou UNKNOWN.

    Une marge de 50 mV au dessus du minimum est consideree comme confortable.
    En dessous du minimum, la desinfection est jugee critique.
    """
    if orp is None:
        return "UNKNOWN"
    if orp >= orp_min + 50:
        return "OK"
    if orp >= orp_min:
        return "LOW"
    return "CRITICAL"


def global_water_status(ph_s: str, cl_s: str, orp_s: str) -> str:
    """Synthetise un statut global lisible a partir des statuts unitaires.

    L'ORP critique prime sur tout le reste car il traduit une desinfection
    insuffisante, qui est le risque sanitaire majeur.
    """
    if orp_s == "CRITICAL":
        return "ORP critical - insufficient disinfection"
    if ph_s == "CRITICAL":
        return "pH critical"
    if ph_s == "HIGH":
        return "pH too high"
    if ph_s == "LOW":
        return "pH too low"
    if cl_s == "LOW":
        return "Insufficient chlorine"
    if cl_s == "HIGH":
        return "Excess chlorine"
    if "UNKNOWN" in (ph_s, cl_s, orp_s):
        return "Missing data"
    return "OK"
