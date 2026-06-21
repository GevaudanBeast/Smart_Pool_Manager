"""Integration SmartPoolManager pour Home Assistant.

Point d'entree de l'integration. Gere la mise en place et le demontage des
entrees de configuration, l'instanciation du coordinator, le chargement des
plateformes (sensor, switch, number, select) et l'enregistrement des services.

Compatible multi-instances : chaque entree de configuration possede son
propre coordinator stocke dans hass.data[DOMAIN][entry_id].
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import SmartPoolCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configure une entree SmartPoolManager.

    On fusionne data (entites, profil) et options (consignes modifiables) pour
    obtenir la configuration effective passee au coordinator.
    """
    hass.data.setdefault(DOMAIN, {})

    # Les options de l'etape 5 surchargent les valeurs initiales si presentes.
    config = {**entry.data, **entry.options}

    coordinator = SmartPoolCoordinator(hass, config, entry.entry_id)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Charger les plateformes d'entites.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Enregistrer les services une seule fois (au premier setup).
    await async_setup_services(hass)

    # Recharger l'entree lorsque les options changent (OptionsFlow).
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info("Entree SmartPoolManager configuree: %s", entry.title)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Demonte une entree SmartPoolManager."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        # Si plus aucune entree active, retirer les services.
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recharge une entree apres modification des options."""
    await hass.config_entries.async_reload(entry.entry_id)
