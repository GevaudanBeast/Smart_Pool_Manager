"""Tests du filtre de plausibilite des mesures de sonde (v0.0.5).

Reproduit le constat du 21/11/2026 : la sonde publiait pH 2.1, TDS 9999,
salinite 9990 g/L et chlore -0.1 mg/L, valeurs traitees comme reelles.
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

from calculations.plausibility import (  # noqa: E402
    PLAUSIBLE_RANGES,
    sanitize_measures,
)


def _raw(**kwargs):
    base = {
        "ph": 7.4,
        "orp": 734.0,
        "cl": 1.5,
        "tds": 3000.0,
        "salinity": 4.0,
        "water_temperature": 17.5,
        "level_low": False,
        "filtration_running": True,
    }
    base.update(kwargs)
    return base


def test_valeurs_du_21_11_rejetees():
    """Les sentinelles observees en production deviennent None."""
    raw = _raw(ph=2.1, tds=9999.0, salinity=9990.0, cl=-0.1)
    clean, rejected = sanitize_measures(raw)
    assert clean["ph"] is None
    assert clean["cl"] is None
    assert clean["tds"] is None
    assert clean["salinity"] is None
    assert set(rejected) == {"ph", "cl", "tds", "salinity"}
    # Les mesures plausibles restent intactes.
    assert clean["orp"] == 734.0
    assert clean["water_temperature"] == 17.5


def test_valeurs_plausibles_conservees():
    raw = _raw()
    clean, rejected = sanitize_measures(raw)
    assert rejected == {}
    assert clean == raw


def test_none_reste_none_sans_rejet():
    clean, rejected = sanitize_measures(_raw(ph=None, tds=None))
    assert clean["ph"] is None
    assert rejected == {}


def test_bornes_incluses():
    low, high = PLAUSIBLE_RANGES["ph"]
    clean, rejected = sanitize_measures(_raw(ph=low))
    assert clean["ph"] == low and rejected == {}
    clean, rejected = sanitize_measures(_raw(ph=high))
    assert clean["ph"] == high and rejected == {}


def test_valeur_rejetee_conservee_pour_diagnostic():
    _, rejected = sanitize_measures(_raw(ph=2.1))
    assert rejected == {"ph": 2.1}


def test_entree_non_modifiee():
    raw = _raw(ph=2.1)
    sanitize_measures(raw)
    assert raw["ph"] == 2.1


def test_cles_non_mesures_ignorees():
    clean, _ = sanitize_measures(_raw(level_low=True))
    assert clean["level_low"] is True
