"""Entites switch exposees par SmartPoolManager.

Deux switches sont exposes :
  - filtration : pilote directement le switch de filtration configure.
  - dosing_auto : active ou desactive le mode de dosage automatique.
"""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DOSING_AUTO, DOMAIN
from .entity import SmartPoolEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Cree les entites switch pour une entree de configuration."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            FiltrationSwitch(coordinator, entry),
            DosingAutoSwitch(coordinator, entry),
        ]
    )


class FiltrationSwitch(SmartPoolEntity, SwitchEntity):
    """Switch de filtration : reflete et pilote le switch de pompe configure."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialise le switch de filtration."""
        super().__init__(coordinator, "filtration")
        self._entry = entry
        self._attr_name = f"{self._pool_name} filtration"

    @property
    def is_on(self) -> bool:
        """Etat reel de la filtration lu via le coordinator."""
        return bool(self.coordinator.data.get("filtration_running", False))

    async def async_turn_on(self, **kwargs) -> None:
        """Allume la filtration."""
        await self.coordinator.async_set_filtration(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Eteint la filtration."""
        await self.coordinator.async_set_filtration(False)
        await self.coordinator.async_request_refresh()


class DosingAutoSwitch(SmartPoolEntity, SwitchEntity):
    """Switch d'activation du mode de dosage automatique.

    L'etat est persiste dans les options de l'entree afin d'etre conserve
    apres un redemarrage de Home Assistant.
    """

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialise le switch de dosage auto."""
        super().__init__(coordinator, "dosing_auto")
        self._entry = entry
        self._attr_name = f"{self._pool_name} dosing auto"

    @property
    def is_on(self) -> bool:
        """Retourne l'etat courant du mode dosage auto."""
        return bool(self.coordinator.config.get(CONF_DOSING_AUTO, True))

    async def async_turn_on(self, **kwargs) -> None:
        """Active le dosage automatique."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Desactive le dosage automatique."""
        await self._async_set(False)

    async def _async_set(self, value: bool) -> None:
        """Met a jour la config en memoire et persiste dans les options."""
        self.coordinator.config[CONF_DOSING_AUTO] = value
        new_options = {**self._entry.options, CONF_DOSING_AUTO: value}
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        _LOGGER.info("Dosage auto %s", "active" if value else "desactive")
        self.async_write_ha_state()
