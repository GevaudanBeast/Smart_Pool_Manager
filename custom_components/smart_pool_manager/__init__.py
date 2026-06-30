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
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)

from .const import DAILY_REPORT_HOUR, DOMAIN, PLATFORMS
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

    # Recalcul evenementiel : on recalcule des qu'un capteur source change
    # d'etat (pas de polling periodique, voir coordinator update_interval=None).
    @callback
    def _async_source_changed(event: Event) -> None:
        """Demande un recalcul quand une entite source change d'etat."""
        hass.async_create_task(coordinator.async_request_refresh())

    source_entities = coordinator.source_entities()
    if source_entities:
        entry.async_on_unload(
            async_track_state_change_event(hass, source_entities, _async_source_changed)
        )

    # Declencheur horaire dedie au rapport quotidien (l'absence de polling
    # periodique ne doit pas empecher l'envoi du rapport a l'heure prevue).
    @callback
    def _async_daily_tick(now) -> None:
        """Force un recalcul a l'heure du rapport quotidien."""
        hass.async_create_task(coordinator.async_request_refresh())

    entry.async_on_unload(
        async_track_time_change(
            hass, _async_daily_tick, hour=DAILY_REPORT_HOUR, minute=0, second=0
        )
    )

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
