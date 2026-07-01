# Changelog

Toutes les evolutions notables de SmartPoolManager sont consignees ici.
Le format suit l'esprit de [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/)
et le projet utilise un versionnage de type SemVer.

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

[0.0.1]: https://github.com/GevaudanBeast/Smart_Pool_Manager/releases/tag/v0.0.1
