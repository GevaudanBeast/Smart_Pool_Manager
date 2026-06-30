"""Tests du moteur de recommandations manuelles.

Couvre la filtration conseillee, les doses en grammes (pH-, pH+, galet, choc),
l'agregation de l'etat global et la robustesse aux mesures manquantes.
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

from calculations.recommendations import (  # noqa: E402
    compute_recommendations,
    recommended_filtration_hours,
)

# Parametres de reference identiques aux defauts de la mission (16 m3).
PARAMS = {
    "ph_target": 7.2,
    "ph_ideal_min": 7.0,
    "ph_ideal_max": 7.4,
    "cl_min": 1.0,
    "cl_max": 3.0,
    "cl_shock": 0.5,
    "orp_min": 650,
    "dose_ph_minus_g": 160,
    "dose_ph_plus_g": 160,
    "dose_choc_g": 320,
    "galet_g": 200,
    "volume_m3": 16.0,
    "ref_volume_m3": 16.0,
}


def _measures(ph=None, cl=None, orp=None, temperature=None):
    """Petit constructeur de dict de mesures."""
    return {"ph": ph, "cl": cl, "orp": orp, "temperature": temperature}


# --- Filtration -----------------------------------------------------------


def test_filtration_temp_pair():
    """28 C / 2 = 14 h."""
    heures, formule = recommended_filtration_hours(28)
    assert heures == 14
    assert "/ 2" in formule


def test_filtration_arrondi():
    """25 C / 2 = 12,5 arrondi a 13 (demi vers le haut)."""
    heures, _ = recommended_filtration_hours(25)
    assert heures == 13


def test_filtration_temp_absente():
    """Temperature inconnue : pas d'heure, formule explicite."""
    heures, formule = recommended_filtration_hours(None)
    assert heures is None
    assert "indisponible" in formule.lower()


# --- pH -------------------------------------------------------------------


def test_ph_dans_cible_aucune_action():
    """pH a 7,2 : eau equilibree, texte vide."""
    res = compute_recommendations(_measures(ph=7.2, cl=2.0, orp=700), PARAMS)
    assert res["etat_global"] == "ok"
    assert res["texte"] == ""


def test_ph_haut_dose_ph_moins():
    """pH 7,6 : round((7,6-7,2)/0,1)=4 paliers x 160 g = 640 g."""
    res = compute_recommendations(_measures(ph=7.6, cl=2.0, orp=700), PARAMS)
    assert res["etat_global"] == "action_requise"
    assert "640 g" in res["texte"]
    assert "pH moins" in res["prochaine_action"]


def test_ph_bas_dose_ph_plus():
    """pH 6,8 : round((7,2-6,8)/0,1)=4 paliers x 160 g = 640 g."""
    res = compute_recommendations(_measures(ph=6.8, cl=2.0, orp=700), PARAMS)
    assert res["etat_global"] == "action_requise"
    assert "640 g" in res["texte"]
    assert "pH plus" in res["prochaine_action"]


def test_ph_leger_un_palier():
    """pH 7,5 : round((7,5-7,2)/0,1)=3 paliers x 160 = 480 g."""
    res = compute_recommendations(_measures(ph=7.5, cl=2.0, orp=700), PARAMS)
    assert "480 g" in res["texte"]


# --- Chlore ---------------------------------------------------------------


def test_chlore_bas_galet():
    """Cl 0,8 (entre 0,5 et 1) : un galet, pas de choc."""
    res = compute_recommendations(_measures(ph=7.2, cl=0.8, orp=700), PARAMS)
    assert res["etat_global"] == "action_requise"
    assert "galet" in res["texte"].lower()
    assert "choc" not in res["texte"].lower()


def test_chlore_tres_bas_choc():
    """Cl 0,3 (<0,5) : galet + chlore choc 320 g."""
    res = compute_recommendations(_measures(ph=7.2, cl=0.3, orp=700), PARAMS)
    assert "galet" in res["texte"].lower()
    assert "320 g" in res["texte"]
    assert "soir" in res["texte"].lower()


def test_chlore_bas_signale_ph_hors_cible():
    """Cl bas ET pH hors cible : on demande de regler le pH d'abord."""
    res = compute_recommendations(_measures(ph=7.6, cl=0.8, orp=700), PARAMS)
    assert "d'abord le ph" in res["texte"].lower()


def test_chlore_haut_retirer_galet():
    """Cl 3,5 (>3) : ne plus ajouter, retirer galet (attention)."""
    res = compute_recommendations(_measures(ph=7.2, cl=3.5, orp=700), PARAMS)
    assert res["etat_global"] == "attention"
    assert "retirez un galet" in res["texte"].lower()


# --- ORP ------------------------------------------------------------------


def test_orp_bas_action():
    """ORP 600 (<650) : eau peu desinfectante."""
    res = compute_recommendations(_measures(ph=7.2, cl=2.0, orp=600), PARAMS)
    assert res["etat_global"] == "action_requise"
    assert "desinfecte mal" in res["texte"].lower()


# --- Volume / mise a l'echelle --------------------------------------------


def test_mise_a_echelle_volume():
    """Volume double : doses doublees."""
    params = dict(PARAMS, volume_m3=32.0)
    res = compute_recommendations(_measures(ph=7.6, cl=2.0, orp=700), params)
    # 4 paliers x 160 g x (32/16) = 1280 g.
    assert "1280 g" in res["texte"]


# --- Robustesse mesures manquantes ----------------------------------------


def test_mesures_absentes_ne_plante_pas():
    """Toutes les mesures None : pas d'exception, etat attention."""
    res = compute_recommendations(_measures(), PARAMS)
    assert res["etat_global"] == "attention"
    assert res["filtration_h"] is None


def test_disclaimer_present_si_dose():
    """Un avertissement de prudence accompagne toute dose de produit."""
    res = compute_recommendations(_measures(ph=7.6, cl=2.0, orp=700), PARAMS)
    assert "verifiez l'emballage" in res["texte"].lower()
