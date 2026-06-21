"""Entites number exposees par SmartPoolManager.

Ces number permettent de modifier les 8 consignes principales directement
depuis l'UI ou un dashboard, sans passer par l'OptionsFlow. Chaque valeur est
ecrite dans la config en memoire du coordinator et persistee dans les options
de l'entree pour survivre a un redemarrage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_CL_TARGET_MG_L,
    CONF_DELAY_BETWEEN_DOSES_MIN,
    CONF_DOSE_MAX_CL_ML,
    CONF_DOSE_MAX_PH_ML,
    CONF_FLOW_RATE_CL_ML_MIN,
    CONF_FLOW_RATE_PH_ML_MIN,
    CONF_ORP_MIN_MV,
    CONF_PH_TARGET,
    DOMAIN,
)
from .entity import SmartPoolEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PoolNumberDescription:
    """Description declarative d'une consigne number.

    Attributes:
        key: cle de configuration associee.
        suffix: suffixe d'entity_id.
        min_value, max_value, step: bornes du curseur.
        default: valeur par defaut.
        unit: unite affichee.
    """

    key: str
    suffix: str
    min_value: float
    max_value: float
    step: float
    default: float
    unit: str | None = None


# Les 8 consignes modifiables exposees comme number.
NUMBERS: tuple[PoolNumberDescription, ...] = (
    PoolNumberDescription(CONF_PH_TARGET, "ph_target", 7.0, 7.8, 0.05, 7.4, "pH"),
    PoolNumberDescription(CONF_CL_TARGET_MG_L, "cl_target", 0.5, 5.0, 0.1, 2.0, "mg/L"),
    PoolNumberDescription(CONF_ORP_MIN_MV, "orp_min", 400, 800, 10, 650, "mV"),
    PoolNumberDescription(CONF_DOSE_MAX_PH_ML, "dose_max_ph_ml", 10, 500, 10, 100, "mL"),
    PoolNumberDescription(CONF_DOSE_MAX_CL_ML, "dose_max_cl_ml", 10, 500, 10, 100, "mL"),
    PoolNumberDescription(
        CONF_DELAY_BETWEEN_DOSES_MIN, "delay_between_doses_min", 30, 480, 10, 60, "min"
    ),
    PoolNumberDescription(
        CONF_FLOW_RATE_PH_ML_MIN, "flow_rate_ph_ml_min", 1.0, 200, 0.5, 30.0, "mL/min"
    ),
    PoolNumberDescription(
        CONF_FLOW_RATE_CL_ML_MIN, "flow_rate_cl_ml_min", 1.0, 200, 0.5, 30.0, "mL/min"
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Cree les entites number pour une entree de configuration."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [SmartPoolNumber(coordinator, entry, desc) for desc in NUMBERS]
    async_add_entities(entities)


class SmartPoolNumber(SmartPoolEntity, NumberEntity):
    """Consigne number generique pilotee par une PoolNumberDescription."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self, coordinator, entry: ConfigEntry, description: PoolNumberDescription
    ) -> None:
        """Initialise la consigne a partir de sa description."""
        super().__init__(coordinator, description.suffix)
        self._desc = description
        self._entry = entry
        self._attr_name = f"{self._pool_name} {description.suffix}"
        self._attr_native_min_value = description.min_value
        self._attr_native_max_value = description.max_value
        self._attr_native_step = description.step
        if description.unit:
            self._attr_native_unit_of_measurement = description.unit

    @property
    def native_value(self) -> float:
        """Valeur courante lue dans la config du coordinator."""
        return float(
            self.coordinator.config.get(self._desc.key, self._desc.default)
        )

    async def async_set_native_value(self, value: float) -> None:
        """Ecrit la nouvelle consigne et la persiste dans les options."""
        self.coordinator.config[self._desc.key] = value
        new_options = {**self._entry.options, self._desc.key: value}
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        _LOGGER.info("Consigne %s mise a jour: %s", self._desc.key, value)
        await self.coordinator.async_request_refresh()
