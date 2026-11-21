"""Tests du mode hivernage passif (v0.0.6).

Contexte du 21/11/2026 : sonde hivernee dans son liquide de conservation
(pH 2.1, TDS 9999, chlore -0.1, 17.5 C de la piece), pompe arretee tout
l'hiver. En mode winter, la sonde est ignoree, aucune alerte ni
recommandation chimique, dosage bloque, aucune ecriture de duree.
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

from calculations.safety import evaluate_safety  # noqa: E402
from calculations.winter import (  # noqa: E402
    PROBE_KEYS,
    WINTER_RECO_ACTION,
    is_winter,
    strip_probe,
    winter_recommendations,
)


def test_is_winter():
    assert is_winter({"filtration_mode": "winter"}) is True
    assert is_winter({"filtration_mode": "auto"}) is False
    assert is_winter({}) is False


def test_strip_probe_vide_toutes_les_mesures_sonde():
    raw = {
        "ph": 2.1,
        "orp": 734.0,
        "cl": -0.1,
        "tds": 9999.0,
        "salinity": 9990.0,
        "water_temperature": 6.6,
        "level_low": True,
        "filtration_running": False,
    }
    clean = strip_probe(raw)
    for key in PROBE_KEYS:
        assert clean[key] is None
    assert clean["water_temperature"] == 6.6
    assert raw["ph"] == 2.1  # entree non modifiee


def test_recommandations_hivernage_sans_produit():
    reco = winter_recommendations()
    assert reco["prochaine_action"] == WINTER_RECO_ACTION
    assert reco["actions"] == []
    texte = reco["texte"].lower()
    for produit in ("ph plus", "ph moins", "chlore", "galet", " g "):
        assert produit not in texte
    assert reco["etat_global"] == "hivernage"


def test_recommandations_hivernage_meme_forme_que_le_mode_normal():
    reco = winter_recommendations()
    for key in (
        "etat_global",
        "prochaine_action",
        "texte",
        "actions",
        "filtration_h",
        "filtration_formule",
    ):
        assert key in reco


def _safe_data(**kwargs):
    data = {
        "level_low": False,
        "filtration_running": True,
        "ph": 7.4,
        "cl": 2.0,
        "last_dose_ph": None,
        "last_dose_cl": None,
        "dosing_ph_running_since_s": 0,
        "dosing_cl_running_since_s": 0,
    }
    data.update(kwargs)
    return data


def test_hivernage_bloque_le_dosage_meme_avec_mesures_correctes():
    result = evaluate_safety(
        _safe_data(winter_mode=True), {"delay_between_doses_min": 60}
    )
    assert result.dosing_ok is False
    assert "Winter mode - dosing disabled" in result.reasons


def test_hors_hivernage_comportement_inchange():
    result = evaluate_safety(
        _safe_data(winter_mode=False), {"delay_between_doses_min": 60}
    )
    assert result.dosing_ok is True
