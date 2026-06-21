"""Coordinator principal de SmartPoolManager.

Ce module contient le DataUpdateCoordinator qui orchestre tout le cycle de
gestion de la piscine : lecture des entites, calcul des durees de filtration,
calcul des doses chimiques, evaluation des regles de securite, declenchement
du dosage automatique et envoi des notifications.

Toutes les operations Home Assistant passent par hass.states.get() et
hass.services.async_call(). Aucune operation bloquante n'est realisee dans la
boucle d'evenements : tout est asynchrone.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .calculations import chemistry, filtration, safety
from .const import (
    CONF_DELAY_BETWEEN_DOSES_MIN,
    CONF_DISINFECTANT_CONCENTRATION_PCT,
    CONF_DOSE_MAX_CL_ML,
    CONF_DOSE_MAX_PH_ML,
    CONF_DOSING_AUTO,
    CONF_ENTITY_CL,
    CONF_ENTITY_LEVEL_LOW,
    CONF_ENTITY_NOTIFY_CRITICAL,
    CONF_ENTITY_NOTIFY_PRIMARY,
    CONF_ENTITY_ORP,
    CONF_ENTITY_PH,
    CONF_ENTITY_PROBE_TEMPERATURE,
    CONF_ENTITY_SALINITY,
    CONF_ENTITY_SO_FILTRATION_DURATION,
    CONF_ENTITY_SO_MAX_DURATION,
    CONF_ENTITY_SWITCH_CL,
    CONF_ENTITY_SWITCH_FILTRATION,
    CONF_ENTITY_SWITCH_PH,
    CONF_ENTITY_TDS,
    CONF_ENTITY_WATER_TEMPERATURE,
    CONF_FLOW_RATE_CL_ML_MIN,
    CONF_FLOW_RATE_PH_ML_MIN,
    CONF_NAME,
    CONF_ORP_MIN_MV,
    CONF_PH_MINUS_CONCENTRATION_PCT,
    CONF_PH_TARGET,
    CONF_PH_TOLERANCE,
    CONF_CL_TARGET_MG_L,
    CONF_CL_TOLERANCE,
    CONF_VOLUME_M3,
    COORDINATOR_UPDATE_INTERVAL,
    DAILY_REPORT_HOUR,
    DOMAIN,
    FALLBACK_WATER_TEMPERATURE,
    PROBE_UNAVAILABLE_ALERT_SECONDS,
    WATCHDOG_MAX_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


def safe_float(state_obj, default=None):
    """Lit un etat HA et retourne un float ou la valeur par defaut.

    Gere les cas None, 'unknown', 'unavailable', chaine vide et les erreurs
    de conversion. A utiliser systematiquement pour lire un etat numerique.
    """
    if state_obj is None:
        return default
    if state_obj.state in ("unknown", "unavailable", ""):
        return default
    try:
        return float(state_obj.state)
    except (ValueError, TypeError):
        return default


def safe_bool(state_obj, default=False) -> bool:
    """Lit un etat HA binary_sensor (ou switch) et retourne un bool.

    Retourne la valeur par defaut si l'etat est absent.
    """
    if state_obj is None:
        return default
    return state_obj.state == "on"


class SmartPoolCoordinator(DataUpdateCoordinator):
    """Coordinator central qui pilote la piscine.

    Une instance par entree de configuration (compatible multi-piscines).
    """

    def __init__(self, hass: HomeAssistant, config: dict, entry_id: str) -> None:
        """Initialise le coordinator.

        Args:
            hass: instance Home Assistant.
            config: dict fusionne data + options de l'entree.
            entry_id: identifiant de l'entree de configuration.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{config.get(CONF_NAME, 'pool')}",
            update_interval=timedelta(seconds=COORDINATOR_UPDATE_INTERVAL),
        )
        self.config = config
        self.entry_id = entry_id

        # Etat interne persistant entre les cycles (dates de dernier dosage,
        # suivi des alertes deja notifiees, etc.).
        self._last_dose_ph: datetime | None = None
        self._last_dose_cl: datetime | None = None
        self._dosing_ph_running = False
        self._dosing_cl_running = False
        self._dosing_ph_start: datetime | None = None
        self._dosing_cl_start: datetime | None = None
        self._probe_unavailable_since: datetime | None = None
        self._last_daily_report_date = None
        self._known_alerts: set[str] = set()
        self._notified_orp_critical = False
        self._notified_probe_unavailable = False

    # ------------------------------------------------------------------
    # Cycle principal
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict:
        """Cycle principal execute toutes les 60 secondes.

        Suit la sequence : lecture entites, calcul filtration, ajustement
        dosage, ecriture Solar Optimizer, calcul doses, securite, dosage
        auto, alertes, notifications.
        """
        _LOGGER.debug("Cycle coordinator %s demarre", self.name)

        # 1 et 2 : lecture des entites et conversion securisee
        raw = self._read_entities()

        # 3 : calcul des durees de filtration
        temperature = raw["water_temperature"]
        if temperature is None:
            # Sans temperature, on retombe sur un palier prudent (eau froide).
            _LOGGER.warning("Temperature eau indisponible, palier prudent applique")
            durations = filtration.calculate_filtration_duration(0)
        else:
            durations = filtration.calculate_filtration_duration(temperature)

        # 6 : calcul des doses chimiques (necessaire pour ajuster la filtration)
        ph_target = float(self.config[CONF_PH_TARGET])
        ph_tolerance = float(self.config[CONF_PH_TOLERANCE])
        cl_target = float(self.config[CONF_CL_TARGET_MG_L])
        cl_tolerance = float(self.config[CONF_CL_TOLERANCE])
        orp_min = float(self.config[CONF_ORP_MIN_MV])
        volume = float(self.config[CONF_VOLUME_M3])

        dosing_ph_ml = 0.0
        dosing_cl_ml = 0.0
        if raw["ph"] is not None:
            dosing_ph_ml = chemistry.calculate_ph_dose(
                raw["ph"],
                ph_target,
                ph_tolerance,
                volume,
                float(self.config[CONF_PH_MINUS_CONCENTRATION_PCT]),
                float(self.config[CONF_DOSE_MAX_PH_ML]),
            )
        if raw["cl"] is not None:
            dosing_cl_ml = chemistry.calculate_cl_dose(
                raw["cl"],
                cl_target,
                cl_tolerance,
                volume,
                float(self.config[CONF_DISINFECTANT_CONCENTRATION_PCT]),
                float(self.config[CONF_DOSE_MAX_CL_ML]),
            )

        flow_ph = float(self.config[CONF_FLOW_RATE_PH_ML_MIN])
        flow_cl = float(self.config[CONF_FLOW_RATE_CL_ML_MIN])
        dosing_ph_duration_s = chemistry.calculate_dose_duration_s(dosing_ph_ml, flow_ph)
        dosing_cl_duration_s = chemistry.calculate_dose_duration_s(dosing_cl_ml, flow_cl)

        # 4 : ajuster la duree min si le dosage planifie depasse la filtration
        durations = filtration.adjust_for_dosing(
            durations, dosing_ph_duration_s + dosing_cl_duration_s
        )

        # Recuperer la duree max autorisee par Solar Optimizer (lecture seule)
        so_max = safe_float(
            self.hass.states.get(self.config[CONF_ENTITY_SO_MAX_DURATION])
        )
        if so_max is not None:
            durations["max"] = int(so_max)
            # On ne recommande jamais plus que la limite imposee par SO.
            if durations["min"] > durations["max"]:
                durations["min"] = durations["max"]
            if durations["recommended"] > durations["max"]:
                durations["recommended"] = durations["max"]

        # 5 : ecrire la duree min calculee dans le helper Solar Optimizer
        await self._async_write_filtration_duration(durations["min"])

        # Statuts chimiques
        ph_status = chemistry.evaluate_ph_status(raw["ph"], ph_target, ph_tolerance)
        cl_status = chemistry.evaluate_cl_status(raw["cl"], cl_target, cl_tolerance)
        orp_status = chemistry.evaluate_orp_status(raw["orp"], orp_min)
        water_status = chemistry.global_water_status(ph_status, cl_status, orp_status)

        # Duree d'activite des pompes pour le watchdog
        now = datetime.now()
        ph_running_since = (
            (now - self._dosing_ph_start).total_seconds()
            if self._dosing_ph_start
            else 0.0
        )
        cl_running_since = (
            (now - self._dosing_cl_start).total_seconds()
            if self._dosing_cl_start
            else 0.0
        )

        # 7 : evaluation des regles de securite
        safety_data = {
            "level_low": raw["level_low"],
            "filtration_running": raw["filtration_running"],
            "ph": raw["ph"],
            "cl": raw["cl"],
            "last_dose_ph": self._last_dose_ph,
            "last_dose_cl": self._last_dose_cl,
            "dosing_ph_running_since_s": ph_running_since,
            "dosing_cl_running_since_s": cl_running_since,
        }
        safety_result = safety.evaluate_safety(
            safety_data,
            {CONF_DELAY_BETWEEN_DOSES_MIN: int(self.config[CONF_DELAY_BETWEEN_DOSES_MIN])},
        )

        # Watchdog : couper d'urgence les pompes si force_stop demande
        if safety_result.force_stop_dosing:
            _LOGGER.error("Watchdog declenche, arret d'urgence des pompes doseuses")
            await self._async_force_stop_pumps()
            await self._async_notify_critical(
                title=f"{NAME_TITLE} - Watchdog",
                message="A dosing pump exceeded the maximum runtime and was stopped.",
            )

        # Construire le dict de donnees expose
        data = {
            # Sonde brute
            "ph": raw["ph"],
            "orp": raw["orp"],
            "cl": raw["cl"],
            "tds": raw["tds"],
            "salinity": raw["salinity"],
            "water_temperature": raw["water_temperature"],
            # Filtration
            "filtration_running": raw["filtration_running"],
            "filtration_recommended_min": durations["recommended"],
            "filtration_min_min": durations["min"],
            "filtration_max_min": durations["max"],
            # Statuts
            "ph_status": ph_status,
            "cl_status": cl_status,
            "orp_status": orp_status,
            "water_status": water_status,
            # Dosage calcule
            "dosing_ph_ml": dosing_ph_ml,
            "dosing_cl_ml": dosing_cl_ml,
            "dosing_ph_duration_s": dosing_ph_duration_s,
            "dosing_cl_duration_s": dosing_cl_duration_s,
            # Etat temps reel dosage
            "dosing_ph_running": self._dosing_ph_running,
            "dosing_cl_running": self._dosing_cl_running,
            "dosing_ph_running_since_s": ph_running_since,
            "dosing_cl_running_since_s": cl_running_since,
            "last_dose_ph": self._last_dose_ph,
            "last_dose_cl": self._last_dose_cl,
            # Securite
            "safety_dosing_ok": safety_result.dosing_ok,
            "safety_filtration_ok": safety_result.filtration_ok,
            "safety_reasons": safety_result.reasons,
            "alert_active": False,
            "alerts": [],
        }

        # Conserver les donnees courantes pour les cycles de dosage qui les lisent
        self.data = data

        # 8 : dosage automatique sous conditions
        dosing_auto = bool(self.config[CONF_DOSING_AUTO])
        if dosing_auto and safety_result.dosing_ok:
            await self._async_run_auto_dosing(
                ph_status, cl_status, dosing_ph_ml, dosing_cl_ml
            )

        # 9 : evaluation des alertes
        alerts = self._evaluate_alerts(
            raw, ph_status, cl_status, orp_status, safety_result, now
        )
        data["alerts"] = alerts
        data["alert_active"] = len(alerts) > 0

        # 10 : notifications evenementielles
        await self._async_handle_notifications(data, orp_status, raw, now)

        # Rapport quotidien a l'heure prevue
        await self._async_maybe_daily_report(data, now)

        _LOGGER.debug("Cycle coordinator %s termine, statut=%s", self.name, water_status)
        return data

    # ------------------------------------------------------------------
    # Lecture des entites
    # ------------------------------------------------------------------

    def _read_entities(self) -> dict:
        """Lit toutes les entites configurees avec conversion securisee."""
        states = self.hass.states

        ph = safe_float(states.get(self.config[CONF_ENTITY_PH]))
        orp = safe_float(states.get(self.config[CONF_ENTITY_ORP]))
        cl = safe_float(states.get(self.config[CONF_ENTITY_CL]))

        tds = None
        if self.config.get(CONF_ENTITY_TDS):
            tds = safe_float(states.get(self.config[CONF_ENTITY_TDS]))

        salinity = None
        if self.config.get(CONF_ENTITY_SALINITY):
            salinity = safe_float(states.get(self.config[CONF_ENTITY_SALINITY]))

        # Temperature eau : sonde dediee si configuree, sinon entite systeme,
        # sinon repli sur le template sensor securise.
        water_temperature = None
        if self.config.get(CONF_ENTITY_PROBE_TEMPERATURE):
            water_temperature = safe_float(
                states.get(self.config[CONF_ENTITY_PROBE_TEMPERATURE])
            )
        if water_temperature is None and self.config.get(CONF_ENTITY_WATER_TEMPERATURE):
            water_temperature = safe_float(
                states.get(self.config[CONF_ENTITY_WATER_TEMPERATURE])
            )
        if water_temperature is None:
            water_temperature = safe_float(states.get(FALLBACK_WATER_TEMPERATURE))

        level_low = safe_bool(states.get(self.config[CONF_ENTITY_LEVEL_LOW]))
        filtration_running = safe_bool(
            states.get(self.config[CONF_ENTITY_SWITCH_FILTRATION])
        )

        return {
            "ph": ph,
            "orp": orp,
            "cl": cl,
            "tds": tds,
            "salinity": salinity,
            "water_temperature": water_temperature,
            "level_low": level_low,
            "filtration_running": filtration_running,
        }

    # ------------------------------------------------------------------
    # Ecriture Solar Optimizer
    # ------------------------------------------------------------------

    async def _async_write_filtration_duration(self, minutes: int) -> None:
        """Ecrit la duree min calculee dans le helper input_number de SO."""
        entity = self.config.get(CONF_ENTITY_SO_FILTRATION_DURATION)
        if not entity:
            return
        try:
            await self.hass.services.async_call(
                "input_number",
                "set_value",
                {"entity_id": entity, "value": minutes},
                blocking=False,
            )
        except Exception as err:  # pragma: no cover - defensif
            _LOGGER.error("Echec ecriture duree filtration vers %s: %s", entity, err)

    # ------------------------------------------------------------------
    # Dosage automatique
    # ------------------------------------------------------------------

    async def _async_run_auto_dosing(
        self,
        ph_status: str,
        cl_status: str,
        dosing_ph_ml: float,
        dosing_cl_ml: float,
    ) -> None:
        """Declenche le dosage auto selon les statuts et l'interlock chimique.

        L'interlock empeche de doser pH et Cl simultanement (reaction
        dangereuse). On ne lance qu'un seul dosage par cycle.
        """
        # pH trop haut et hors tolerance : dosage pH si pas de dosage Cl en cours
        if (
            ph_status in ("HIGH", "CRITICAL")
            and dosing_ph_ml > 0.0
            and not self._dosing_cl_running
            and not self._dosing_ph_running
        ):
            delay_ok = self._delay_elapsed(self._last_dose_ph)
            if delay_ok:
                _LOGGER.info("Dosage pH auto declenche (%.1f mL)", dosing_ph_ml)
                self.hass.async_create_task(self._async_dose_ph())
                return

        # Cl trop bas et hors tolerance : dosage Cl si pas de dosage pH en cours
        if (
            cl_status == "LOW"
            and dosing_cl_ml > 0.0
            and not self._dosing_ph_running
            and not self._dosing_cl_running
        ):
            delay_ok = self._delay_elapsed(self._last_dose_cl)
            if delay_ok:
                _LOGGER.info("Dosage Cl auto declenche (%.1f mL)", dosing_cl_ml)
                self.hass.async_create_task(self._async_dose_cl())

    def _delay_elapsed(self, last_dose: datetime | None) -> bool:
        """Verifie que le delai minimal entre deux doses est ecoule."""
        if last_dose is None:
            return True
        elapsed = (datetime.now() - last_dose).total_seconds()
        return elapsed >= int(self.config[CONF_DELAY_BETWEEN_DOSES_MIN]) * 60

    async def _async_dose_ph(self) -> None:
        """Cycle de dosage pH automatique ou manuel.

        Regle absolue : toujours eteindre la pompe dans le bloc finally.
        Interlock : ne pas lancer si un dosage Cl est en cours.
        """
        if self._dosing_cl_running:
            _LOGGER.warning("Dosage pH ignore : dosage Cl en cours (interlock)")
            return
        self._dosing_ph_running = True
        self._dosing_ph_start = datetime.now()
        self.data["dosing_ph_running"] = True
        self.data["dosing_ph_running_since_s"] = 0.0
        try:
            await self.hass.services.async_call(
                "switch",
                "turn_on",
                {"entity_id": self.config[CONF_ENTITY_SWITCH_PH]},
                blocking=True,
            )
            duration_s = min(int(self.data["dosing_ph_duration_s"]), WATCHDOG_MAX_SECONDS)
            _LOGGER.info("Pompe pH active pour %s secondes", duration_s)
            await asyncio.sleep(duration_s)
            self._last_dose_ph = datetime.now()
            self.data["last_dose_ph"] = self._last_dose_ph
            await self._async_notify_primary(
                title=f"{NAME_TITLE} - pH Dosing",
                message=(
                    f"pH- dose completed: {self.data['dosing_ph_ml']} mL "
                    f"in {duration_s}s"
                ),
            )
        finally:
            await self.hass.services.async_call(
                "switch",
                "turn_off",
                {"entity_id": self.config[CONF_ENTITY_SWITCH_PH]},
                blocking=True,
            )
            self._dosing_ph_running = False
            self._dosing_ph_start = None
            self.data["dosing_ph_running"] = False
            self.data["dosing_ph_running_since_s"] = 0.0
            _LOGGER.info("Pompe pH arretee")

    async def _async_dose_cl(self) -> None:
        """Cycle de dosage Cl automatique ou manuel.

        Miroir de _async_dose_ph pour le desinfectant.
        Interlock : ne pas lancer si un dosage pH est en cours.
        Regle absolue : toujours eteindre la pompe dans le bloc finally.
        """
        if self._dosing_ph_running:
            _LOGGER.warning("Dosage Cl ignore : dosage pH en cours (interlock)")
            return
        self._dosing_cl_running = True
        self._dosing_cl_start = datetime.now()
        self.data["dosing_cl_running"] = True
        self.data["dosing_cl_running_since_s"] = 0.0
        try:
            await self.hass.services.async_call(
                "switch",
                "turn_on",
                {"entity_id": self.config[CONF_ENTITY_SWITCH_CL]},
                blocking=True,
            )
            duration_s = min(int(self.data["dosing_cl_duration_s"]), WATCHDOG_MAX_SECONDS)
            _LOGGER.info("Pompe Cl active pour %s secondes", duration_s)
            await asyncio.sleep(duration_s)
            self._last_dose_cl = datetime.now()
            self.data["last_dose_cl"] = self._last_dose_cl
            await self._async_notify_primary(
                title=f"{NAME_TITLE} - Cl Dosing",
                message=(
                    f"Cl dose completed: {self.data['dosing_cl_ml']} mL "
                    f"in {duration_s}s"
                ),
            )
        finally:
            await self.hass.services.async_call(
                "switch",
                "turn_off",
                {"entity_id": self.config[CONF_ENTITY_SWITCH_CL]},
                blocking=True,
            )
            self._dosing_cl_running = False
            self._dosing_cl_start = None
            self.data["dosing_cl_running"] = False
            self.data["dosing_cl_running_since_s"] = 0.0
            _LOGGER.info("Pompe Cl arretee")

    async def _async_force_stop_pumps(self) -> None:
        """Coupe immediatement les deux pompes doseuses (watchdog)."""
        for entity in (
            self.config[CONF_ENTITY_SWITCH_PH],
            self.config[CONF_ENTITY_SWITCH_CL],
        ):
            try:
                await self.hass.services.async_call(
                    "switch", "turn_off", {"entity_id": entity}, blocking=True
                )
            except Exception as err:  # pragma: no cover - defensif
                _LOGGER.error("Echec arret pompe %s: %s", entity, err)
        self._dosing_ph_running = False
        self._dosing_cl_running = False
        self._dosing_ph_start = None
        self._dosing_cl_start = None

    # ------------------------------------------------------------------
    # Filtration : commande directe
    # ------------------------------------------------------------------

    async def async_set_filtration(self, turn_on: bool) -> None:
        """Allume ou eteint la filtration via le switch configure."""
        service = "turn_on" if turn_on else "turn_off"
        _LOGGER.info("Filtration %s demandee", "ON" if turn_on else "OFF")
        await self.hass.services.async_call(
            "switch",
            service,
            {"entity_id": self.config[CONF_ENTITY_SWITCH_FILTRATION]},
            blocking=True,
        )

    # ------------------------------------------------------------------
    # Alertes
    # ------------------------------------------------------------------

    def _evaluate_alerts(
        self,
        raw: dict,
        ph_status: str,
        cl_status: str,
        orp_status: str,
        safety_result: safety.SafetyResult,
        now: datetime,
    ) -> list[str]:
        """Construit la liste des alertes actives a un instant donne."""
        alerts: list[str] = []

        if orp_status == "CRITICAL":
            alerts.append("ORP critical - insufficient disinfection")
        if ph_status == "CRITICAL":
            alerts.append("pH critical")
        if cl_status == "LOW":
            alerts.append("Chlorine too low")
        if raw["level_low"]:
            alerts.append("Water level low")

        # Suivi de l'indisponibilite sonde
        if raw["ph"] is None or raw["cl"] is None:
            if self._probe_unavailable_since is None:
                self._probe_unavailable_since = now
            unavailable_for = (now - self._probe_unavailable_since).total_seconds()
            if unavailable_for > PROBE_UNAVAILABLE_ALERT_SECONDS:
                alerts.append("Probe unavailable for more than 2 hours")
        else:
            self._probe_unavailable_since = None

        # Raisons de blocage securite remontees comme alertes
        for reason in safety_result.reasons:
            if reason not in alerts:
                alerts.append(reason)

        return alerts

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    async def _async_handle_notifications(
        self, data: dict, orp_status: str, raw: dict, now: datetime
    ) -> None:
        """Envoie les notifications evenementielles (ORP, sonde, etc.)."""
        # ORP critique : notification critique unique tant que l'etat persiste
        if orp_status == "CRITICAL":
            if not self._notified_orp_critical:
                await self._async_notify_critical(
                    title=f"{NAME_TITLE} - ORP Critical",
                    message="ORP is critically low, disinfection insufficient.",
                )
                self._notified_orp_critical = True
        else:
            self._notified_orp_critical = False

        # Sonde indisponible depuis plus de 2h
        if (
            self._probe_unavailable_since is not None
            and (now - self._probe_unavailable_since).total_seconds()
            > PROBE_UNAVAILABLE_ALERT_SECONDS
        ):
            if not self._notified_probe_unavailable:
                await self._async_notify_primary(
                    title=f"{NAME_TITLE} - Probe Unavailable",
                    message="Pool probe has been unavailable for more than 2 hours.",
                )
                self._notified_probe_unavailable = True
        else:
            self._notified_probe_unavailable = False

    async def _async_maybe_daily_report(self, data: dict, now: datetime) -> None:
        """Envoie le rapport quotidien a l'heure prevue si une alerte est active."""
        if now.hour != DAILY_REPORT_HOUR:
            return
        if self._last_daily_report_date == now.date():
            return
        self._last_daily_report_date = now.date()
        if not data["alert_active"]:
            return

        pool_name = self.config.get(CONF_NAME, "Pool")
        alerts = ", ".join(data["alerts"]) if data["alerts"] else "None"
        message = (
            f"pH      : {data['ph']} ({data['ph_status']})\n"
            f"ORP     : {data['orp']} mV ({data['orp_status']})\n"
            f"Cl      : {data['cl']} mg/L ({data['cl_status']})\n"
            f"Temp    : {data['water_temperature']} C\n"
            f"Recommended filtration : {data['filtration_recommended_min']} min "
            f"(min: {data['filtration_min_min']} / max: {data['filtration_max_min']})\n"
            f"pH dose needed         : {data['dosing_ph_ml']} mL "
            f"({data['dosing_ph_duration_s']} s pump time)\n"
            f"Cl dose needed         : {data['dosing_cl_ml']} mL "
            f"({data['dosing_cl_duration_s']} s pump time)\n"
            f"Active alerts : {alerts}"
        )
        await self._async_notify_primary(
            title=f"{NAME_TITLE} - Daily Report {pool_name} {now.date()}",
            message=message,
        )

    async def _async_notify_primary(self, title: str, message: str) -> None:
        """Envoie une notification au destinataire principal."""
        target = self.config[CONF_ENTITY_NOTIFY_PRIMARY].replace("notify.", "")
        try:
            await self.hass.services.async_call(
                "notify",
                target,
                {"title": title, "message": message},
                blocking=False,
            )
        except Exception as err:  # pragma: no cover - defensif
            _LOGGER.error("Echec notification principale: %s", err)

    async def _async_notify_critical(self, title: str, message: str) -> None:
        """Envoie une notification critique aux deux destinataires."""
        for entity in (
            self.config[CONF_ENTITY_NOTIFY_PRIMARY],
            self.config[CONF_ENTITY_NOTIFY_CRITICAL],
        ):
            target = entity.replace("notify.", "")
            try:
                await self.hass.services.async_call(
                    "notify",
                    target,
                    {"title": title, "message": message},
                    blocking=False,
                )
            except Exception as err:  # pragma: no cover - defensif
                _LOGGER.error("Echec notification critique vers %s: %s", target, err)


# Titre lisible utilise dans les notifications. Defini ici pour eviter une
# dependance circulaire avec const lors de l'import du module.
NAME_TITLE = "SmartPoolManager"
