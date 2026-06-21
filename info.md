# SmartPoolManager

Gestion complete d'une piscine dans Home Assistant : filtration, chimie de
l'eau (pH, Cl, ORP), dosage automatique et securite. Configuration entierement
via l'interface, sans YAML.

## Points cles

- Calcul de la duree de filtration selon la temperature, ecrit dans les
  helpers Solar Optimizer.
- Lecture d'une sonde 7-en-1 et evaluation des statuts pH / Cl / ORP.
- Dosage automatique pH- et desinfectant avec interlock chimique.
- Securite : pas de dosage si filtration arretee ou niveau bas, watchdog
  pompes, delai entre doses.
- Notifications et rapport quotidien.
- Multi-piscines.

Apres installation, ajouter l'integration via
**Parametres > Appareils et services > Ajouter une integration >
SmartPoolManager** et suivre les 5 etapes de configuration.

Voir le [README](https://github.com/GevaudanBeast/Smart_Pool_Manager) pour le
detail des entites, services et du dashboard fourni.
