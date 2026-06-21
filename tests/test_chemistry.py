"""Tests des calculs chimiques.

Couvre le calcul des doses pH et Cl, la conversion dose vers duree, ainsi
que l'evaluation des statuts.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "smart_pool_manager",
    ),
)

from calculations.chemistry import (  # noqa: E402
    calculate_cl_dose,
    calculate_dose_duration_s,
    calculate_ph_dose,
    evaluate_cl_status,
    evaluate_orp_status,
    evaluate_ph_status,
    global_water_status,
)


def test_ph_dose_within_tolerance():
    """pH dans la tolerance : pas de dosage."""
    assert calculate_ph_dose(7.5, 7.4, 0.2, 16.0, 14.0, 100) == 0.0


def test_ph_dose_at_target():
    """pH egal a la cible : pas de dosage."""
    assert calculate_ph_dose(7.4, 7.4, 0.2, 16.0, 14.0, 100) == 0.0


def test_ph_dose_slightly_high():
    """pH legerement haut : dose positive plafonnee a dose_max."""
    dose = calculate_ph_dose(7.7, 7.4, 0.2, 16.0, 14.0, 100)
    assert dose > 0.0
    assert dose <= 100


def test_ph_dose_very_high_capped():
    """pH tres haut : dose plafonnee a dose_max."""
    dose = calculate_ph_dose(9.0, 7.4, 0.2, 50.0, 14.0, 100)
    assert dose == 100


def test_ph_dose_concentration_adjusted():
    """Une concentration plus faible donne une dose plus grande."""
    dose_14 = calculate_ph_dose(7.8, 7.4, 0.0, 2.0, 14.0, 500)
    dose_7 = calculate_ph_dose(7.8, 7.4, 0.0, 2.0, 7.0, 500)
    # A 7 pour cent, il faut deux fois plus de produit qu'a 14 pour cent.
    assert round(dose_7, 1) == round(dose_14 * 2, 1)


def test_cl_dose_within_tolerance():
    """Cl dans la tolerance : pas de dosage."""
    assert calculate_cl_dose(1.8, 2.0, 0.5, 16.0, 14.0, 100) == 0.0


def test_cl_dose_at_target():
    assert calculate_cl_dose(2.0, 2.0, 0.5, 16.0, 14.0, 100) == 0.0


def test_cl_dose_low():
    """Cl bas : dose positive."""
    dose = calculate_cl_dose(0.5, 2.0, 0.1, 16.0, 14.0, 500)
    assert dose > 0.0


def test_cl_dose_capped():
    """Cl tres bas : dose plafonnee."""
    dose = calculate_cl_dose(0.0, 5.0, 0.0, 100.0, 14.0, 100)
    assert dose == 100


def test_cl_dose_concentration_adjusted():
    dose_14 = calculate_cl_dose(0.0, 2.0, 0.0, 16.0, 14.0, 5000)
    dose_7 = calculate_cl_dose(0.0, 2.0, 0.0, 16.0, 7.0, 5000)
    assert round(dose_7, 1) == round(dose_14 * 2, 1)


def test_dose_duration_zero_dose():
    assert calculate_dose_duration_s(0, 30) == 0


def test_dose_duration_nominal():
    assert calculate_dose_duration_s(30, 30) == 60


def test_dose_duration_zero_flow():
    assert calculate_dose_duration_s(30, 0) == 0


def test_ph_status_variants():
    assert evaluate_ph_status(None, 7.4, 0.2) == "UNKNOWN"
    assert evaluate_ph_status(7.4, 7.4, 0.2) == "OK"
    assert evaluate_ph_status(7.7, 7.4, 0.2) == "HIGH"
    assert evaluate_ph_status(8.5, 7.4, 0.2) == "CRITICAL"
    assert evaluate_ph_status(7.0, 7.4, 0.2) == "LOW"
    assert evaluate_ph_status(6.0, 7.4, 0.2) == "CRITICAL"


def test_cl_status_variants():
    assert evaluate_cl_status(None, 2.0, 0.5) == "UNKNOWN"
    assert evaluate_cl_status(2.0, 2.0, 0.5) == "OK"
    assert evaluate_cl_status(3.0, 2.0, 0.5) == "HIGH"
    assert evaluate_cl_status(1.0, 2.0, 0.5) == "LOW"


def test_orp_status_variants():
    assert evaluate_orp_status(None, 650) == "UNKNOWN"
    assert evaluate_orp_status(720, 650) == "OK"
    assert evaluate_orp_status(660, 650) == "LOW"
    assert evaluate_orp_status(600, 650) == "CRITICAL"


def test_global_water_status_priority():
    # ORP critique prime sur tout
    assert (
        global_water_status("HIGH", "LOW", "CRITICAL")
        == "ORP critical - insufficient disinfection"
    )
    assert global_water_status("CRITICAL", "OK", "OK") == "pH critical"
    assert global_water_status("HIGH", "OK", "OK") == "pH too high"
    assert global_water_status("LOW", "OK", "OK") == "pH too low"
    assert global_water_status("OK", "LOW", "OK") == "Insufficient chlorine"
    assert global_water_status("OK", "HIGH", "OK") == "Excess chlorine"
    assert global_water_status("UNKNOWN", "OK", "OK") == "Missing data"
    assert global_water_status("OK", "OK", "OK") == "OK"
