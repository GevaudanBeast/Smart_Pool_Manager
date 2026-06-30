"""Recommandations manuelles pour SmartPoolManager.

Ce module contient des fonctions pures (aucune dependance Home Assistant) qui
transforment les mesures de la sonde en conseils concrets, exprimes en
grammes de produit du commerce (galets de chlore lent, chlore choc en poudre,
pH moins en poudre, pH plus en poudre).

Il complete le module chemistry.py, qui lui calcule des doses en mL pour le
dosage automatique par pompes. Ici on s'adresse a l'utilisateur qui dose a la
main : le texte produit est en francais simple, sans jargon.

Toutes les doses sont des ordres de grandeur parametrables. Elles ne doivent
jamais etre presentees comme des certitudes : un avertissement invitant a
verifier l'emballage et a doser progressivement est ajoute des qu'une dose de
produit est conseillee.
"""

from __future__ import annotations

import math

# Niveaux de gravite renvoyes pour l'etat global.
ETAT_OK = "ok"
ETAT_ATTENTION = "attention"
ETAT_ACTION = "action_requise"


def _round_half_up(value: float) -> int:
    """Arrondit a l'entier le plus proche (0,5 arrondi vers le haut).

    On evite l'arrondi "banquier" de la fonction round() native de Python,
    qui arrondirait 2,5 vers 2 et surprendrait l'utilisateur.
    """
    return int(math.floor(value + 0.5))


def _round_to_10(value: float) -> int:
    """Arrondit une dose en grammes a la dizaine la plus proche.

    Une dose affichee "environ 480 g" est plus lisible et plus honnete qu'une
    fausse precision du type "478,3 g".
    """
    return int(_round_half_up(value / 10.0) * 10)


def recommended_filtration_hours(temperature: float | None) -> tuple[int | None, str]:
    """Calcule la duree de filtration conseillee en heures par jour.

    Regle de la mission : temperature de l'eau divisee par deux, arrondie a
    l'entier.

    Returns:
        Un tuple (heures, formule). heures vaut None si la temperature est
        indisponible ; formule est une chaine explicative pour l'attribut.
    """
    if temperature is None:
        return None, "Temperature de l'eau indisponible"
    heures = max(0, _round_half_up(temperature / 2.0))
    formule = f"temperature eau / 2 = {temperature} / 2 = {heures} h/jour"
    return heures, formule


def compute_recommendations(measures: dict, params: dict) -> dict:
    """Construit les recommandations manuelles a partir des mesures.

    Args:
        measures: dict avec les cles ph, cl (chlore libre mg/L), orp, temperature.
            Chaque valeur peut etre None si la sonde est indisponible.
        params: dict des reglages (cibles, seuils, doses unitaires, volume).
            Cles attendues : ph_target, ph_ideal_min, ph_ideal_max, cl_min,
            cl_max, cl_shock, orp_min, dose_ph_minus_g, dose_ph_plus_g,
            dose_choc_g, galet_g, volume_m3, ref_volume_m3.

    Returns:
        Un dict : etat_global, prochaine_action, texte, actions (liste),
        filtration_h, filtration_formule.
    """
    ph = measures.get("ph")
    cl = measures.get("cl")
    orp = measures.get("orp")
    temperature = measures.get("temperature")

    # Facteur d'echelle : les doses de reference sont donnees pour un volume
    # de reference (16 m3 par defaut). On adapte lineairement au volume reel.
    ref_volume = params.get("ref_volume_m3") or 16.0
    volume = params.get("volume_m3") or ref_volume
    scale = volume / ref_volume if ref_volume else 1.0

    ph_target = params["ph_target"]
    ph_lo = params["ph_ideal_min"]
    ph_hi = params["ph_ideal_max"]

    actions: list[dict] = []
    notes: list[str] = []

    # --- pH ---------------------------------------------------------------
    ph_off = False
    if ph is None:
        notes.append("pH non disponible : correction du pH impossible a conseiller.")
    elif ph > ph_hi:
        ph_off = True
        paliers = max(1, _round_half_up((ph - ph_target) / 0.1))
        dose = _round_to_10(paliers * params["dose_ph_minus_g"] * scale)
        actions.append(
            {
                "sev": ETAT_ACTION,
                "has_dose": True,
                "titre": f"Baisser le pH : environ {dose} g de pH moins",
                "texte": (
                    f"Le pH est trop haut ({ph}). Ajoutez environ {dose} g de "
                    "pH moins en poudre, laissez filtrer puis recontrolez apres "
                    "quelques heures."
                ),
            }
        )
    elif ph < ph_lo:
        ph_off = True
        paliers = max(1, _round_half_up((ph_target - ph) / 0.1))
        dose = _round_to_10(paliers * params["dose_ph_plus_g"] * scale)
        actions.append(
            {
                "sev": ETAT_ACTION,
                "has_dose": True,
                "titre": f"Monter le pH : environ {dose} g de pH plus",
                "texte": (
                    f"Le pH est trop bas ({ph}). Ajoutez environ {dose} g de "
                    "pH plus en poudre, laissez filtrer puis recontrolez apres "
                    "quelques heures."
                ),
            }
        )

    # --- ORP --------------------------------------------------------------
    if orp is not None and orp < params["orp_min"]:
        if ph_off:
            suite = "Reglez d'abord le pH (voir ci-dessus), puis ajustez le chlore."
        else:
            suite = "Verifiez le pH puis renforcez le chlore."
        actions.append(
            {
                "sev": ETAT_ACTION,
                "has_dose": False,
                "titre": "ORP bas : eau peu desinfectante",
                "texte": (f"L'ORP est bas ({orp} mV), l'eau desinfecte mal. {suite}"),
            }
        )

    # --- Chlore libre -----------------------------------------------------
    if cl is None:
        notes.append("Chlore libre non disponible : conseil sur le chlore impossible.")
    elif cl < params["cl_min"]:
        morceaux: list[str] = []
        if ph_off:
            morceaux.append(
                "Reglez d'abord le pH (voir ci-dessus) pour que le chlore agisse."
            )
        morceaux.append(
            f"Placez 1 galet de chlore lent ({int(params['galet_g'])} g) "
            "dans le skimmer."
        )
        if cl < params["cl_shock"]:
            dose_choc = _round_to_10(params["dose_choc_g"] * scale)
            morceaux.append(
                f"Chlore tres bas : ajoutez aussi environ {dose_choc} g de "
                "chlore choc en poudre le soir, filtration en marche."
            )
        actions.append(
            {
                "sev": ETAT_ACTION,
                "has_dose": True,
                "titre": "Chlore bas : ajouter du chlore",
                "texte": (
                    f"Le chlore libre est bas ({cl} mg/L). " + " ".join(morceaux)
                ),
            }
        )
    elif cl > params["cl_max"]:
        actions.append(
            {
                "sev": ETAT_ATTENTION,
                "has_dose": False,
                "titre": "Chlore haut : laisser baisser",
                "texte": (
                    f"Le chlore libre est eleve ({cl} mg/L). N'ajoutez plus de "
                    "chlore, retirez un galet du skimmer et laissez le taux "
                    "redescendre avant la baignade."
                ),
            }
        )

    # --- Etat global ------------------------------------------------------
    if any(a["sev"] == ETAT_ACTION for a in actions):
        etat = ETAT_ACTION
    elif actions or notes:
        etat = ETAT_ATTENTION
    else:
        etat = ETAT_OK

    # --- Filtration -------------------------------------------------------
    filtration_h, filtration_formule = recommended_filtration_hours(temperature)

    # --- Texte lisible ----------------------------------------------------
    if not actions and not notes:
        texte = ""
        prochaine = "Aucune action, eau equilibree."
    else:
        lignes: list[str] = []
        for index, action in enumerate(actions, start=1):
            lignes.append(f"{index}. {action['texte']}")
        for note in notes:
            lignes.append(f"- {note}")
        if any(a["has_dose"] for a in actions):
            lignes.append("")
            lignes.append(
                f"Doses indicatives pour {round(volume)} m3. Verifiez "
                "l'emballage du produit et dosez progressivement."
            )
        texte = "\n".join(lignes)
        prochaine = actions[0]["titre"] if actions else notes[0]

    return {
        "etat_global": etat,
        "prochaine_action": prochaine,
        "texte": texte,
        "actions": actions,
        "filtration_h": filtration_h,
        "filtration_formule": filtration_formule,
    }
