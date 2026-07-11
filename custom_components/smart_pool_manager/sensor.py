"""Entites sensor exposees par SmartPoolManager.

Toutes les valeurs proviennent du coordinator. Chaque sensor est defini de
maniere declarative (cle de donnee, unite, device_class) puis instancie a
partir d'une liste de descriptions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import SmartPoolEntity


@dataclass(frozen=True)
class PoolSensorDescription:
    """Description declarative d'un sensor.

    Attributes:
        key: cle dans le dict du coordinator.
        suffix: suffixe d'entity_id.
        unit: unite de mesure (ou None).
        device_class: device_class HA (ou None).
        is_json: True si la valeur est une liste a serialiser en JSON.
    """

    key: str
    suffix: str
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    is_json: bool = False
    # Cle du dict coordinator contenant les attributs supplementaires (ou None).
    attrs_key: str | None = None
    # Icone Material Design optionnelle.
    icon: str | None = None


# Definition declarative de tous les sensors a exposer.
SENSORS: tuple[PoolSensorDescription, ...] = (
    PoolSensorDescription("ph", "ph", "pH"),
    PoolSensorDescription("orp", "orp", "mV"),
    PoolSensorDescription("cl", "cl", "mg/L"),
    PoolSensorDescription("tds", "tds", "ppm"),
    PoolSensorDescription("salinity", "salinity", "g/L"),
    PoolSensorDescription(
        "water_temperature", "water_temperature", "°C", SensorDeviceClass.TEMPERATURE
    ),
    PoolSensorDescription("ph_status", "ph_status"),
    PoolSensorDescription("cl_status", "cl_status"),
    PoolSensorDescription("orp_status", "orp_status"),
    PoolSensorDescription("water_status", "water_status"),
    PoolSensorDescription(
        "filtration_recommended_min", "filtration_recommended_min", "min"
    ),
    PoolSensorDescription("filtration_min_min", "filtration_min_min", "min"),
    PoolSensorDescription("filtration_max_min", "filtration_max_min", "min"),
    PoolSensorDescription("dosing_ph_ml", "dosing_ph_ml", "mL"),
    PoolSensorDescription("dosing_cl_ml", "dosing_cl_ml", "mL"),
    PoolSensorDescription(
        "dosing_ph_duration_s", "dosing_ph_duration_s", "s", SensorDeviceClass.DURATION
    ),
    PoolSensorDescription(
        "dosing_cl_duration_s", "dosing_cl_duration_s", "s", SensorDeviceClass.DURATION
    ),
    PoolSensorDescription(
        "last_dose_ph", "last_dose_ph", None, SensorDeviceClass.TIMESTAMP
    ),
    PoolSensorDescription(
        "last_dose_cl", "last_dose_cl", None, SensorDeviceClass.TIMESTAMP
    ),
    PoolSensorDescription("alerts", "alerts", is_json=True),
    # --- Recommandations manuelles (conseil utilisateur en grammes) ---
    PoolSensorDescription(
        "reco_filtration_h",
        "filtration_conseillee",
        "h",
        attrs_key="reco_filtration_attrs",
        icon="mdi:timer-cog-outline",
    ),
    PoolSensorDescription("reco_etat_global", "etat_global", icon="mdi:pool"),
    PoolSensorDescription(
        "reco_prochaine_action", "prochaine_action", icon="mdi:clipboard-alert-outline"
    ),
    PoolSensorDescription(
        "reco_recommandations", "recommandations", icon="mdi:clipboard-list-outline"
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Cree les entites sensor pour une entree de configuration."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [SmartPoolSensor(coordinator, desc) for desc in SENSORS]
    async_add_entities(entities)


class SmartPoolSensor(SmartPoolEntity, SensorEntity):
    """Sensor generique pilote par une PoolSensorDescription."""

    def __init__(self, coordinator, description: PoolSensorDescription) -> None:
        """Initialise le sensor a partir de sa description."""
        super().__init__(coordinator, description.suffix)
        self._desc = description
        self._attr_name = f"{self._pool_name} {description.suffix}"
        if description.unit:
            self._attr_native_unit_of_measurement = description.unit
        if description.device_class:
            self._attr_device_class = description.device_class
        if description.icon:
            self._attr_icon = description.icon
        # Les valeurs numeriques de mesure recoivent une state_class measurement.
        if description.device_class == SensorDeviceClass.TEMPERATURE:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    # Limite stricte d'un state Home Assistant. Au dela, HA rejette la valeur
    # et le capteur retombe sur "unknown". On tronque donc la valeur exposee.
    _MAX_STATE_LENGTH = 255

    def _raw_value(self):
        """Retourne la valeur brute exploitable (str si concernee).

        Serialise la liste JSON le cas echeant. Utilise a la fois par
        native_value et extra_state_attributes pour rester coherent.
        """
        value = self.coordinator.data.get(self._desc.key)
        if self._desc.is_json:
            # Serialise la liste d'alertes en chaine JSON exploitable cote UI.
            return json.dumps(value or [])
        return value

    @property
    def native_value(self):
        """Retourne la valeur courante, tronquee si elle depasse 255 caracteres."""
        value = self._raw_value()
        if isinstance(value, str) and len(value) > self._MAX_STATE_LENGTH:
            # 252 caracteres + "..." = 255 caracteres au total.
            return value[:252] + "..."
        return value

    @property
    def extra_state_attributes(self) -> dict | None:
        """Expose les attributs supplementaires du capteur.

        Publie les attributs definis par la description (par exemple la
        formule de calcul de la filtration conseillee) et, si la valeur du
        state a du etre tronquee a 255 caracteres, expose le texte integral
        dans la cle texte_complet. Les deux sources sont fusionnees.
        """
        attrs: dict = {}
        if self._desc.attrs_key:
            base = self.coordinator.data.get(self._desc.attrs_key)
            if base:
                attrs.update(base)

        value = self._raw_value()
        if isinstance(value, str) and len(value) > self._MAX_STATE_LENGTH:
            attrs["texte_complet"] = value

        return attrs or None
