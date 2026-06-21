"""Entite select exposee par SmartPoolManager.

Expose le mode de filtration sous forme de selecteur. Le choix est applique
immediatement : auto laisse le calcul automatique piloter, force_on et
force_off forcent l'etat de la pompe, winter applique un mode hivernage.
"""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, FILTRATION_MODES
from .entity import SmartPoolEntity

_LOGGER = logging.getLogger(__name__)

# Cle de stockage du mode courant dans les options de l'entree.
CONF_FILTRATION_MODE = "filtration_mode"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Cree l'entite select pour une entree de configuration."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FiltrationModeSelect(coordinator, entry)])


class FiltrationModeSelect(SmartPoolEntity, SelectEntity):
    """Selecteur du mode de filtration."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialise le selecteur."""
        super().__init__(coordinator, "filtration_mode")
        self._entry = entry
        self._attr_name = f"{self._pool_name} filtration mode"
        self._attr_options = list(FILTRATION_MODES)

    @property
    def current_option(self) -> str:
        """Mode courant, par defaut auto."""
        return self.coordinator.config.get(CONF_FILTRATION_MODE, "auto")

    async def async_select_option(self, option: str) -> None:
        """Applique le mode choisi et le persiste."""
        if option not in FILTRATION_MODES:
            _LOGGER.warning("Mode de filtration inconnu ignore: %s", option)
            return
        self.coordinator.config[CONF_FILTRATION_MODE] = option
        new_options = {**self._entry.options, CONF_FILTRATION_MODE: option}
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        _LOGGER.info("Mode de filtration: %s", option)

        # Application immediate des modes forces.
        if option == "force_on":
            await self.coordinator.async_set_filtration(True)
        elif option in ("force_off", "winter"):
            await self.coordinator.async_set_filtration(False)

        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()
