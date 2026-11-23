"""Mode hivernage passif pour SmartPoolManager.

Fonctions pures, sans dependance Home Assistant. En hivernage passif, la
pompe est arretee tout l'hiver et la sonde est stockee dans son liquide de
conservation : ses mesures ne decrivent pas l'eau. On les ignore toutes,
on ne produit ni alerte ni recommandation chimique, et la duree de
filtration n'est plus ecrite vers Solar Optimizer.
"""

from __future__ import annotations

WINTER_MODE = "winter"
CONF_FILTRATION_MODE = "filtration_mode"

# Mesures fournies par la sonde, ignorees en hivernage. La temperature d'eau
# n'en fait pas partie : en hivernage elle vient de la source de secours.
PROBE_KEYS = ("ph", "orp", "cl", "tds", "salinity")

ETAT_HIVERNAGE = "hivernage"
WINTER_RECO_ACTION = "Hivernage : aucune action chimique"


def is_winter(config: dict) -> bool:
    """Indique si le mode de filtration courant est l'hivernage."""
    return config.get(CONF_FILTRATION_MODE) == WINTER_MODE


def strip_probe(raw: dict) -> dict:
    """Renvoie une copie de raw ou toutes les mesures de sonde valent None."""
    clean = dict(raw)
    for key in PROBE_KEYS:
        clean[key] = None
    return clean


def winter_recommendations() -> dict:
    """Recommandations en hivernage : aucune action, meme forme que le mode normal."""
    return {
        "etat_global": ETAT_HIVERNAGE,
        "prochaine_action": WINTER_RECO_ACTION,
        "texte": "Hivernage passif : sonde ignoree, pompe arretee, "
        "aucune recommandation de produit.",
        "actions": [],
        "filtration_h": 0,
        "filtration_formule": "Hivernage passif : pompe arretee",
    }
