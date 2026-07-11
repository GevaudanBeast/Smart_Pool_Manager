# SmartPoolManager

Gestion complete d'une piscine dans Home Assistant : filtration, chimie de
l'eau (pH, chlore, ORP), conseils de dosage manuel, dosage automatique et
securite. Configuration entierement via l'interface, sans YAML.

L'integration fonctionne dans deux modes complementaires, actifs en meme
temps :

- **Mode conseil (manuel)** : elle indique en francais simple quoi faire et
  quelle quantite de produit du commerce mettre (galets, poudres), en grammes.
  Aucune pompe necessaire.
- **Mode automatique (optionnel)** : si vous disposez de pompes doseuses, elle
  calcule les volumes en mL et pilote les pompes.

## Points cles

- Capteurs de recommandation : `etat_global` (ok / attention / action_requise),
  `prochaine_action` et `recommandations` (texte chiffre, vide si tout va bien).
- Filtration conseillee en heures par jour selon la temperature de l'eau, avec
  la formule en attribut ; duree min / max ecrite dans les helpers Solar
  Optimizer pour le mode automatique.
- Lecture d'une sonde Zigbee (pH, ORP, chlore libre, TDS, salinite,
  temperature) et evaluation des statuts.
- Notifications quand l'etat passe a `action_requise` (persistante, plus mobile
  si configuree), et journalisation dans le logbook.
- Securite : aucun dosage si la filtration est arretee ou le niveau bas,
  watchdog d'arret d'urgence des pompes, delai minimal entre deux doses.
- Recalcul evenementiel (pas de polling) et support multi-piscines.

Apres installation, ajouter l'integration via
**Parametres > Appareils et services > Ajouter une integration >
SmartPoolManager** et suivre les 6 etapes de configuration (les pompes
doseuses peuvent rester vides pour n'utiliser que le mode conseil).

> Les doses affichees sont des ordres de grandeur. Verifiez toujours
> l'emballage du produit et dosez progressivement.

Voir le [README](https://github.com/GevaudanBeast/Smart_Pool_Manager) pour le
detail des entites, services et du dashboard fourni.
