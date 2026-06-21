"""Classe de base partagee pour les entites SmartPoolManager.

Fournit le rattachement au coordinator, le device_info commun (toutes les
entites d'une piscine apparaissent sous un meme appareil) et la construction
du prefixe d'unique_id base sur le slug du nom de la piscine.
"""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import CONF_NAME, DOMAIN
from .coordinator import SmartPoolCoordinator


class SmartPoolEntity(CoordinatorEntity[SmartPoolCoordinator]):
    """Entite de base reliee au coordinator d'une piscine."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: SmartPoolCoordinator, suffix: str) -> None:
        """Initialise l'entite.

        Args:
            coordinator: coordinator de la piscine.
            suffix: suffixe technique (ex: "ph", "filtration").
        """
        super().__init__(coordinator)
        self._suffix = suffix
        pool_name = coordinator.config.get(CONF_NAME, "pool")
        self._pool_slug = slugify(pool_name)
        # Prefixe d'unique_id : smart_pool_manager_<pool_slug>_<suffix>
        self._attr_unique_id = f"{DOMAIN}_{self._pool_slug}_{suffix}"
        self._pool_name = pool_name

    @property
    def device_info(self) -> DeviceInfo:
        """Regroupe toutes les entites de la piscine sous un seul appareil."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry_id)},
            name=self._pool_name,
            manufacturer="SmartPoolManager",
            model="Pool Controller",
        )
