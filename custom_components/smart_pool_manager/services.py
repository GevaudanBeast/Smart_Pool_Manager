"""Services Home Assistant exposes par SmartPoolManager.

Declare et enregistre les 4 services :
  - dose_ph : declenche un cycle de dosage pH manuel immediat.
  - dose_cl : declenche un cycle de dosage Cl manuel immediat.
  - set_filtration_mode : force un mode de filtration.
  - reload : recharge toutes les entrees sans redemarrer HA.

Les services resolvent la piscine cible via entry_id. Si une seule piscine
est configuree, entry_id est optionnel.
"""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    FILTRATION_MODES,
    SERVICE_DOSE_CL,
    SERVICE_DOSE_PH,
    SERVICE_EVALUER,
    SERVICE_NOTIFIER,
    SERVICE_RELOAD,
    SERVICE_SET_FILTRATION_MODE,
)

_LOGGER = logging.getLogger(__name__)

# Cle de stockage du mode de filtration (alignee sur select.py).
CONF_FILTRATION_MODE = "filtration_mode"

DOSE_SCHEMA = vol.Schema({vol.Optional("entry_id"): cv.string})
SET_MODE_SCHEMA = vol.Schema(
    {
        vol.Required("mode"): vol.In(FILTRATION_MODES),
        vol.Optional("entry_id"): cv.string,
    }
)


def _resolve_coordinator(hass: HomeAssistant, call: ServiceCall):
    """Retrouve le coordinator cible a partir d'un entry_id optionnel.

    Si aucun entry_id n'est fourni et qu'une seule piscine existe, celle-ci
    est utilisee. Sinon une erreur explicite est levee.
    """
    coordinators = hass.data.get(DOMAIN, {})
    if not coordinators:
        raise HomeAssistantError("No SmartPoolManager instance configured")

    entry_id = call.data.get("entry_id")
    if entry_id:
        coordinator = coordinators.get(entry_id)
        if coordinator is None:
            raise HomeAssistantError(f"Unknown entry_id: {entry_id}")
        return coordinator

    if len(coordinators) == 1:
        return next(iter(coordinators.values()))

    raise HomeAssistantError(
        "Multiple pools configured, entry_id is required for this service"
    )


async def async_setup_services(hass: HomeAssistant) -> None:
    """Enregistre les services s'ils ne le sont pas deja."""
    if hass.services.has_service(DOMAIN, SERVICE_DOSE_PH):
        return

    async def async_dose_ph(call: ServiceCall) -> None:
        """Declenche un cycle de dosage pH manuel."""
        coordinator = _resolve_coordinator(hass, call)
        _LOGGER.info("Service dose_ph appele")
        await coordinator._async_dose_ph()

    async def async_dose_cl(call: ServiceCall) -> None:
        """Declenche un cycle de dosage Cl manuel."""
        coordinator = _resolve_coordinator(hass, call)
        _LOGGER.info("Service dose_cl appele")
        await coordinator._async_dose_cl()

    async def async_set_filtration_mode(call: ServiceCall) -> None:
        """Force un mode de filtration."""
        coordinator = _resolve_coordinator(hass, call)
        mode = call.data["mode"]
        _LOGGER.info("Service set_filtration_mode: %s", mode)
        coordinator.config[CONF_FILTRATION_MODE] = mode
        if mode == "force_on":
            await coordinator.async_set_filtration(True)
        elif mode in ("force_off", "winter"):
            await coordinator.async_set_filtration(False)
        await coordinator.async_request_refresh()

    async def async_reload(call: ServiceCall) -> None:
        """Recharge toutes les entrees de l'integration."""
        _LOGGER.info("Service reload appele")
        entries = hass.config_entries.async_entries(DOMAIN)
        for entry in entries:
            await hass.config_entries.async_reload(entry.entry_id)

    async def async_evaluer(call: ServiceCall) -> ServiceResponse:
        """Recalcule immediatement et renvoie le texte de recommandation."""
        coordinator = _resolve_coordinator(hass, call)
        _LOGGER.info("Service evaluer appele")
        return await coordinator.async_evaluate()

    async def async_notifier(call: ServiceCall) -> ServiceResponse:
        """Declenche l'envoi d'une notification avec le texte de reco."""
        coordinator = _resolve_coordinator(hass, call)
        _LOGGER.info("Service notifier appele")
        return await coordinator.async_send_reco_notification()

    hass.services.async_register(
        DOMAIN, SERVICE_DOSE_PH, async_dose_ph, schema=DOSE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DOSE_CL, async_dose_cl, schema=DOSE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FILTRATION_MODE,
        async_set_filtration_mode,
        schema=SET_MODE_SCHEMA,
    )
    hass.services.async_register(DOMAIN, SERVICE_RELOAD, async_reload)
    hass.services.async_register(
        DOMAIN,
        SERVICE_EVALUER,
        async_evaluer,
        schema=DOSE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_NOTIFIER,
        async_notifier,
        schema=DOSE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    _LOGGER.debug("Services SmartPoolManager enregistres")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Retire les services (appele quand plus aucune entree n'est active)."""
    for service in (
        SERVICE_DOSE_PH,
        SERVICE_DOSE_CL,
        SERVICE_SET_FILTRATION_MODE,
        SERVICE_RELOAD,
        SERVICE_EVALUER,
        SERVICE_NOTIFIER,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
