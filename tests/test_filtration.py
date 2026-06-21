"""Tests des calculs de duree de filtration.

Couvre calculate_filtration_duration sur chaque palier de temperature et
adjust_for_dosing pour les cas dosage court et dosage long.
"""

from __future__ import annotations

import os
import sys

# Permet d'importer le module calculations sans installer le package complet.
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "smart_pool_manager",
    ),
)

from calculations.filtration import (  # noqa: E402
    adjust_for_dosing,
    calculate_filtration_duration,
)


def test_duration_very_cold():
    """T inferieure a 12 degres : palier le plus bas."""
    assert calculate_filtration_duration(0) == {
        "recommended": 120,
        "min": 60,
        "max": 180,
    }


def test_duration_14c():
    assert calculate_filtration_duration(14) == {
        "recommended": 240,
        "min": 180,
        "max": 300,
    }


def test_duration_18c():
    assert calculate_filtration_duration(18) == {
        "recommended": 360,
        "min": 240,
        "max": 480,
    }


def test_duration_22c():
    assert calculate_filtration_duration(22) == {
        "recommended": 480,
        "min": 360,
        "max": 600,
    }


def test_duration_26c():
    assert calculate_filtration_duration(26) == {
        "recommended": 600,
        "min": 480,
        "max": 720,
    }


def test_duration_30c():
    assert calculate_filtration_duration(30) == {
        "recommended": 720,
        "min": 600,
        "max": 840,
    }


def test_adjust_short_dosing_unchanged():
    """Un dosage court ne doit pas allonger la duree min."""
    durations = {"recommended": 480, "min": 360, "max": 600}
    # 60 secondes de dosage + 30 min de tampon = 31 min, bien sous les 360 min
    result = adjust_for_dosing(durations, 60)
    assert result["min"] == 360
    assert result["recommended"] == 480


def test_adjust_long_dosing_extends_min():
    """Un dosage long doit etendre la duree min pour couvrir dosage + 30 min."""
    durations = {"recommended": 120, "min": 60, "max": 180}
    # 3600 secondes (60 min) de dosage + 30 min de tampon = 90 min requis
    result = adjust_for_dosing(durations, 3600)
    assert result["min"] == 90
    assert result["recommended"] == 120  # recommended >= min, inchange ici


def test_adjust_long_dosing_pushes_recommended():
    """Si le requis depasse aussi le recommended, ce dernier suit."""
    durations = {"recommended": 120, "min": 60, "max": 180}
    # 9000 secondes (150 min) + 30 min de tampon = 180 min requis
    result = adjust_for_dosing(durations, 9000)
    assert result["min"] == 180
    assert result["recommended"] == 180
