# Changelog

Toutes les evolutions notables de SmartPoolManager sont consignees ici.
Le format suit l'esprit de [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/)
et le projet utilise un versionnage de type SemVer.

## [Non publie]

### Ajoute

- **Etape Notifications dans les options** : les trois services de
  notification (`entity_notify_primary`, `entity_notify_critical` et le service
  des recommandations `reco_notify_service`) sont desormais modifiables depuis
  l'interface (bouton Configurer > Notifications), sans avoir a supprimer et
  recreer l'integration.

### Corrige

- **Ouverture des options (erreur 500)** : l'OptionsFlow definissait
  `self.config_entry` dans son `__init__`, ce que les versions recentes de Home
  Assistant n'autorisent plus (la propriete `config_entry` est fournie par le
  framework). Cela renvoyait une « 500 Internal Server Error » a l'ouverture des
  parametres. Le constructeur a ete retire.

### Modifie

- Les services de notification par defaut pointent desormais vers
  `notify.notify` (present sur toute installation) au lieu de
  `notify.mobile_app_owner` / `notify.mobile_app_secondary`, qui n'existaient
  pas forcement et provoquaient des echecs d'envoi.

## [0.0.2] - 2026-07-11

### Corrige

- **Datetime sans fuseau horaire (dosage).** Les capteurs `last_dose_ph` et
  `last_dose_cl` ont la `device_class` `timestamp` mais recevaient un
  `datetime.now()` naif, rejete par Home Assistant (« missing timezone
  information »). Le coordinator utilise desormais
  `homeassistant.util.dt.now()` pour tous les horodatages. Le module de calculs
  `calculations/safety.py` reste pur (aucun import Home Assistant) et gere les
  deux cas via une fonction `_elapsed_seconds(last)` : comparaison naive si
  `last.tzinfo is None`, sinon comparaison en UTC. Cela couvre a la fois les
  tests (datetime naifs) et le runtime (datetime avec fuseau).

- **Recommandations de plus de 255 caracteres.** Un state Home Assistant est
  limite a 255 caracteres ; au dela, la valeur etait rejetee et le capteur
  `recommandations` affichait « unknown ». Les capteurs texte tronquent
  maintenant leur valeur a 252 caracteres suivis de `...`, et exposent le texte
  integral dans l'attribut `texte_complet` (fusionne avec les attributs
  existants) lorsque la troncature a lieu.

- **Notifications vers un service inexistant.** Les appels `notify` echouaient
  en boucle quand la cible configuree n'existait pas. Le coordinator verifie
  desormais la disponibilite du service via `_notify_target_available(target)`
  (`hass.services.has_service("notify", target)`) avant chaque appel dans
  `_async_notify_primary`, `_async_notify_critical` et la partie mobile de
  `_async_notify_reco`. L'appel est saute si le service manque, et le warning
  n'est emis qu'une seule fois par cible (memorise dans
  `self._missing_notify_warned`).

### Connu / a corriger ailleurs (hors composant)

- **Valeurs `number.capteurs_piscine_*` hors plage** (par ex. `ph=1400`,
  `orp=-1`, `free_chlorine=-1`). Ces erreurs proviennent de la sonde MQTT
  externe (prefixe `capteurs_piscine`), et non de ce composant. Elles doivent
  etre corrigees cote firmware ESP ou dans la configuration du MQTT discovery
  (bornes `min`/`max` et validation des valeurs publiees). Aucun changement de
  code dans SmartPoolManager n'est requis pour ce point.

## [0.0.1] - 2026-06-30

Premiere release publique de l'integration Home Assistant SmartPoolManager.

L'integration fonctionne dans deux modes complementaires, actifs en meme temps :
un mode conseil (dosage manuel, quantites en grammes) et un mode automatique
(pilotage de pompes doseuses, volumes en mL).

### Ajoute

- **Mode conseil manuel** : capteurs `etat_global` (ok / attention /
  action_requise), `prochaine_action` (resume court) et `recommandations`
  (texte multi-lignes en francais avec les quantites chiffrees, vide si tout
  va bien).
- **Filtration conseillee** : capteur `filtration_conseillee` en heures par
  jour (temperature de l'eau divisee par deux), avec la formule en attribut.
- **Doses en grammes** : pH moins et pH plus par paliers de 0,1 (160 g par
  defaut), galet de chlore lent (200 g), chlore choc (320 g) si le chlore
  libre passe sous 0,5 mg/L, retrait de galet si le chlore depasse 3 mg/L.
- **Mode automatique** : calcul des volumes de pH moins et de desinfectant en
  mL, pilotage des pompes peristaltiques avec interlock chimique (jamais pH et
  Cl en meme temps).
- **Securite** : aucun dosage si la filtration est arretee ou le niveau bas,
  watchdog d'arret d'urgence des pompes, delai minimal entre deux doses.
- **Notifications** : a la transition vers `action_requise`, notification
  persistante et notification mobile (si configuree). Service cible
  parametrable, par defaut `persistent_notification`.
- **Journalisation** : chaque changement d'action prioritaire est inscrit
  dans le logbook de Home Assistant.
- **Services** : `evaluer` (recalcule et renvoie le texte de recommandation),
  `notifier` (envoie la notification), `dose_ph`, `dose_cl`,
  `set_filtration_mode`, `reload`.
- **Recalcul evenementiel** : recalcul a chaque changement d'etat des capteurs
  sources, avec un declencheur horaire dedie pour le rapport quotidien.
- **Configuration par l'interface** : assistant en 6 etapes (profil, sonde,
  pompes, systeme, consignes chimiques, recommandations) et OptionsFlow a deux
  entrees. Tout est parametrable, sans YAML.
- **Installation avec la seule sonde** : les entites de dosage (pompes) et
  d'automatisation (filtration, niveau, helpers Solar Optimizer) sont
  facultatives. On peut donc installer l'integration en mode conseil seul,
  sans aucun materiel de dosage.
- **Multi-piscines** : plusieurs instances en parallele.
- **Dashboard Lovelace** pret a importer et traductions francais / anglais.

### Notes

- Les doses affichees sont des ordres de grandeur. Verifiez toujours
  l'emballage du produit et dosez progressivement.
- Les entites sont exposees sous le domaine `smart_pool_manager`
  (par exemple `sensor.smart_pool_manager_<slug>_etat_global`).

[0.0.2]: https://github.com/GevaudanBeast/Smart_Pool_Manager/releases/tag/v0.0.2
[0.0.1]: https://github.com/GevaudanBeast/Smart_Pool_Manager/releases/tag/v0.0.1
