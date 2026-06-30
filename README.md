# SmartPoolManager

[![Validate](https://github.com/GevaudanBeast/Smart_Pool_Manager/actions/workflows/validate.yaml/badge.svg)](https://github.com/GevaudanBeast/Smart_Pool_Manager/actions/workflows/validate.yaml)
[![Tests](https://github.com/GevaudanBeast/Smart_Pool_Manager/actions/workflows/tests.yaml/badge.svg)](https://github.com/GevaudanBeast/Smart_Pool_Manager/actions/workflows/tests.yaml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Custom integration Home Assistant pour la gestion complete d'une piscine :
filtration, chimie de l'eau (pH, Cl, ORP), conseils de dosage manuel,
dosage automatique et securite. Tout se configure via l'interface, sans YAML.

L'integration fonctionne dans deux modes complementaires, actifs en meme
temps :

- **Mode conseil (manuel)** : elle vous dit, en francais simple, quoi faire
  et quelle quantite de produit du commerce mettre (galets, poudres), en
  grammes. Aucune pompe necessaire.
- **Mode automatique** : si vous disposez de pompes doseuses, elle calcule les
  volumes en mL et pilote les pompes.

## Fonctionnalites

- **Recommandations en clair** : capteurs `etat_global` (ok / attention /
  action_requise), `prochaine_action` (resume court) et `recommandations`
  (texte multi-lignes avec les quantites chiffrees, vide si tout va bien).
- **Filtration conseillee** : capteur `filtration_conseillee` en heures par
  jour (temperature de l'eau divisee par deux), avec la formule en attribut.
- **Notifications utiles** : quand l'etat passe a `action_requise`, envoi
  d'une notification persistante et, si configure, d'une notification mobile.
  Le service cible est parametrable (defaut `persistent_notification`).
- **Journalisation** : chaque changement d'action prioritaire est inscrit
  dans le logbook de Home Assistant.
- **Filtration intelligente (mode auto)** : duree recommandee / min / max
  selon la temperature, ecrite dans les helpers Solar Optimizer.
- **Chimie de l'eau** : lecture d'une sonde Zigbee (pH, ORP, chlore libre,
  TDS, salinite, temperature) et evaluation des statuts.
- **Dosage automatique (optionnel)** : volumes de pH- et de desinfectant,
  pilotage des pompes peristaltiques, interlock chimique (jamais pH et Cl en
  meme temps).
- **Securite** : aucun dosage si la filtration est arretee ou le niveau bas,
  watchdog d'arret d'urgence des pompes, delai minimal entre deux doses.
- **Recalcul evenementiel** : recalcul a chaque changement d'etat des
  capteurs sources (pas de polling periodique).
- **Multi-piscines** : plusieurs instances en parallele.

## Installation

### Via HACS (recommande)

1. HACS doit etre installe dans Home Assistant.
2. HACS > Integrations > menu (trois points) > **Custom repositories**.
3. Ajouter `https://github.com/GevaudanBeast/Smart_Pool_Manager` avec la
   categorie **Integration**.
4. Rechercher **SmartPoolManager** et installer.
5. Redemarrer Home Assistant.

### Manuelle

Copier le dossier `custom_components/smart_pool_manager` dans le repertoire
`config/custom_components/` de Home Assistant, puis redemarrer.

## Configuration

Parametres > Appareils et services > **Ajouter une integration** >
**SmartPoolManager**. L'assistant se deroule en 6 etapes :

1. **Profil piscine** : nom, volume (defaut 16 m3), type de traitement,
   concentrations.
2. **Entites sonde** : pH, ORP, chlore libre (requis), TDS, salinite,
   temperature (optionnels). Les entity_id de la sonde Zigbee varient selon le
   pairing Zigbee2MQTT, d'ou la configuration via l'UI. Pour la sonde decrite
   ici, on selectionne par exemple `sensor.capteurs_piscine_ph`,
   `sensor.capteurs_piscine_free_chlorine`, `sensor.capteurs_piscine_orp` et
   `sensor.capteurs_piscine_temperature`.
3. **Pompes doseuses** : relais ON/OFF, vitesses, debits. A laisser vide si
   vous dosez a la main (mode conseil seul).
4. **Entites systeme** : filtration, niveau bas, temperature eau et helpers
   Solar Optimizer.
5. **Consignes chimiques (dosage auto)** : cibles, tolerances, doses max,
   delais, etc.
6. **Recommandations manuelles** : cibles pH (pivot 7,2 ; ideal 7,0 a 7,4),
   seuils chlore (mini 1, maxi 3, choc < 0,5 mg/L), doses unitaires des
   produits en grammes (pH moins et pH plus 160 g par palier de 0,1 ; chlore
   choc 320 g ; galet 200 g ; volume de reference 16 m3) et le service de
   notification (defaut `persistent_notification`, sinon `notify.mobile_app_xxx`).

Les etapes 5 et 6 sont modifiables a tout moment via le bouton **Configurer**
de l'integration (OptionsFlow, menu a deux entrees), sans toucher aux entites.

> Les doses affichees sont des ordres de grandeur. Verifiez toujours
> l'emballage du produit et dosez progressivement.

## Entites exposees

Prefixe : `smart_pool_manager_<pool_slug>_` ou `pool_slug` est derive du nom.

| Plateforme | Exemples |
|------------|----------|
| `sensor` (conseil) | `etat_global`, `prochaine_action`, `recommandations`, `filtration_conseillee` (attribut `formule`) |
| `sensor` (mesures) | ph, orp, cl, tds, salinity, water_temperature, *_status, filtration_*, dosing_*, last_dose_*, alerts |
| `switch`   | filtration, dosing_auto |
| `number`   | ph_target, cl_target, orp_min, dose_max_ph_ml, dose_max_cl_ml, delay_between_doses_min, flow_rate_ph_ml_min, flow_rate_cl_ml_min |
| `select`   | filtration_mode (auto / force_on / force_off / winter) |

Exemple d'identifiants pour une piscine nommee "Ma piscine" :
`sensor.smart_pool_manager_ma_piscine_etat_global`,
`sensor.smart_pool_manager_ma_piscine_recommandations`, etc.

## Services

| Service | Description |
|---------|-------------|
| `smart_pool_manager.evaluer` | Recalcule immediatement et renvoie le texte de recommandation |
| `smart_pool_manager.notifier` | Envoie une notification avec les recommandations courantes |
| `smart_pool_manager.dose_ph` | Cycle de dosage pH manuel immediat (pompe) |
| `smart_pool_manager.dose_cl` | Cycle de dosage Cl manuel immediat (pompe) |
| `smart_pool_manager.set_filtration_mode` | Forcer un mode de filtration |
| `smart_pool_manager.reload` | Recharger la configuration sans redemarrer HA |

`entry_id` est optionnel si une seule piscine est configuree. Les services
`evaluer` et `notifier` renvoient une reponse (texte de reco) exploitable dans
un script via `response_variable`.

## Dashboard

Un dashboard Lovelace pret a importer est fourni dans
`custom_components/smart_pool_manager/lovelace/dashboard.yaml`. Remplacer
`<pool_slug>` par le slug reel de votre piscine apres installation, puis
coller dans l'editeur de configuration brute d'un nouveau dashboard.

## Developpement et tests

Les calculs metier (filtration, chimie, securite) sont des fonctions pures
sans dependance Home Assistant, couvertes par des tests pytest.

```bash
pip install -r requirements_test.txt
pytest -q
```

Lint et formatage avec [ruff](https://docs.astral.sh/ruff/) :

```bash
ruff check custom_components tests
ruff format --check custom_components tests
```

## Architecture

```
custom_components/smart_pool_manager/
    __init__.py          # mise en place des entrees, ecoute des sources, services
    config_flow.py       # assistant UI 6 etapes + OptionsFlow (menu)
    coordinator.py       # DataUpdateCoordinator (recalcul evenementiel)
    const.py             # constantes et cles de configuration
    entity.py            # classe de base des entites
    sensor.py / switch.py / number.py / select.py
    services.py / services.yaml
    calculations/        # filtration.py, chemistry.py, safety.py, recommendations.py (purs)
    translations/        # fr.json, en.json
    lovelace/            # dashboard.yaml
tests/                   # test_filtration.py, test_chemistry.py, test_safety.py, test_recommendations.py
```

## Licence

Distribue sous licence MIT. Voir [LICENSE](LICENSE).
