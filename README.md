# SmartPoolManager

[![Validate](https://github.com/GevaudanBeast/Smart_Pool_Manager/actions/workflows/validate.yaml/badge.svg)](https://github.com/GevaudanBeast/Smart_Pool_Manager/actions/workflows/validate.yaml)
[![Tests](https://github.com/GevaudanBeast/Smart_Pool_Manager/actions/workflows/tests.yaml/badge.svg)](https://github.com/GevaudanBeast/Smart_Pool_Manager/actions/workflows/tests.yaml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Custom integration Home Assistant pour la gestion complete d'une piscine :
filtration, chimie de l'eau (pH, Cl, ORP), dosage automatique et securite.
Tout se configure via l'interface, sans YAML.

## Fonctionnalites

- **Filtration intelligente** : calcul de la duree recommandee / min / max
  selon la temperature de l'eau, ecrite dans les helpers Solar Optimizer
  (qui reste maitre de l'optimisation solaire).
- **Chimie de l'eau** : lecture d'une sonde 7-en-1 (pH, ORP, Cl, TDS,
  salinite, temperature) et evaluation des statuts.
- **Dosage automatique** : calcul des volumes de pH- et de desinfectant a
  injecter, pilotage des pompes peristaltiques, avec interlock chimique
  (jamais pH et Cl en meme temps).
- **Securite** : aucun dosage si la filtration est arretee ou le niveau bas,
  watchdog d'arret d'urgence des pompes, delai minimal entre deux doses.
- **Notifications** : dosage effectue, ORP critique, sonde indisponible,
  watchdog, et rapport quotidien.
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
**SmartPoolManager**. L'assistant se deroule en 5 etapes :

1. **Profil piscine** : nom, volume, type de traitement, concentrations.
2. **Entites sonde** : pH, ORP, Cl (requis), TDS, salinite, temperature
   (optionnels). Les entity_id de la sonde Zigbee varient selon le pairing
   Zigbee2MQTT, d'ou la configuration via l'UI.
3. **Pompes doseuses** : relais ON/OFF, vitesses (optionnel), debits.
4. **Entites systeme** : filtration, niveau bas, temperature eau et helpers
   Solar Optimizer.
5. **Consignes chimiques** : cibles, tolerances, doses max, delais, etc.

Les consignes de l'etape 5 sont modifiables a tout moment via le bouton
**Configurer** de l'integration (OptionsFlow), sans toucher aux entites.

## Entites exposees

Prefixe : `smart_pool_manager_<pool_slug>_` ou `pool_slug` est derive du nom.

| Plateforme | Exemples |
|------------|----------|
| `sensor`   | ph, orp, cl, tds, salinity, water_temperature, *_status, filtration_*, dosing_*, last_dose_*, alerts |
| `switch`   | filtration, dosing_auto |
| `number`   | ph_target, cl_target, orp_min, dose_max_ph_ml, dose_max_cl_ml, delay_between_doses_min, flow_rate_ph_ml_min, flow_rate_cl_ml_min |
| `select`   | filtration_mode (auto / force_on / force_off / winter) |

## Services

| Service | Description |
|---------|-------------|
| `smart_pool_manager.dose_ph` | Cycle de dosage pH manuel immediat |
| `smart_pool_manager.dose_cl` | Cycle de dosage Cl manuel immediat |
| `smart_pool_manager.set_filtration_mode` | Forcer un mode de filtration |
| `smart_pool_manager.reload` | Recharger la configuration sans redemarrer HA |

`entry_id` est optionnel si une seule piscine est configuree.

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
    __init__.py          # mise en place des entrees et services
    config_flow.py       # assistant UI 5 etapes + OptionsFlow
    coordinator.py       # DataUpdateCoordinator (cycle 60s)
    const.py             # constantes et cles de configuration
    entity.py            # classe de base des entites
    sensor.py / switch.py / number.py / select.py
    services.py / services.yaml
    calculations/        # filtration.py, chemistry.py, safety.py (purs)
    translations/        # fr.json, en.json
    lovelace/            # dashboard.yaml
tests/                   # test_filtration.py, test_chemistry.py, test_safety.py
```

## Licence

Distribue sous licence MIT. Voir [LICENSE](LICENSE).
