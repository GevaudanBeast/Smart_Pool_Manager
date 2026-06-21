"""Constantes partagees pour l'integration SmartPoolManager.

Ce fichier centralise toutes les cles de configuration, les valeurs par
defaut et les constantes techniques utilisees par les autres modules.
Le but est d'eviter les chaines magiques dispersees dans le code.
"""

from __future__ import annotations

# Identite de l'integration
DOMAIN = "smart_pool_manager"
NAME = "SmartPoolManager"

# Parametres du coordinator
COORDINATOR_UPDATE_INTERVAL = 60  # secondes entre deux cycles de calcul

# Securite
WATCHDOG_MAX_SECONDS = 3600  # duree max d'activite d'une pompe doseuse (1 heure)

# Rapport quotidien
DAILY_REPORT_HOUR = 8  # heure d'envoi du rapport quotidien (08h00 locale)

# Duree maximale d'indisponibilite sonde avant notification (secondes)
PROBE_UNAVAILABLE_ALERT_SECONDS = 7200  # 2 heures

# Tampon de filtration ajoute lorsqu'un dosage est planifie (secondes)
DOSING_FILTRATION_BUFFER_SECONDS = 1800  # 30 minutes

# Cles du dict de configuration (etape 1 : profil piscine)
CONF_NAME = "name"
CONF_VOLUME_M3 = "volume_m3"
CONF_TREATMENT_TYPE = "treatment_type"
CONF_PH_MINUS_CONCENTRATION_PCT = "ph_minus_concentration_pct"
CONF_DISINFECTANT_CONCENTRATION_PCT = "disinfectant_concentration_pct"

# Cles de configuration (etape 2 : entites sonde)
CONF_ENTITY_PH = "entity_ph"
CONF_ENTITY_ORP = "entity_orp"
CONF_ENTITY_CL = "entity_cl"
CONF_ENTITY_TDS = "entity_tds"
CONF_ENTITY_SALINITY = "entity_salinity"
CONF_ENTITY_PROBE_TEMPERATURE = "entity_probe_temperature"

# Cles de configuration (etape 3 : pompes doseuses)
CONF_ENTITY_SWITCH_PH = "entity_switch_ph"
CONF_ENTITY_SWITCH_CL = "entity_switch_cl"
CONF_ENTITY_NUMBER_PH_SPEED = "entity_number_ph_speed"
CONF_ENTITY_NUMBER_CL_SPEED = "entity_number_cl_speed"
CONF_FLOW_RATE_PH_ML_MIN = "flow_rate_ph_ml_min"
CONF_FLOW_RATE_CL_ML_MIN = "flow_rate_cl_ml_min"

# Cles de configuration (etape 4 : entites systeme)
CONF_ENTITY_SWITCH_FILTRATION = "entity_switch_filtration"
CONF_ENTITY_LEVEL_LOW = "entity_level_low"
CONF_ENTITY_WATER_TEMPERATURE = "entity_water_temperature"
CONF_ENTITY_SO_FILTRATION_DURATION = "entity_so_filtration_duration"
CONF_ENTITY_SO_MAX_DURATION = "entity_so_max_duration"

# Cles de configuration (etape 5 : consignes chimiques, modifiables via options)
CONF_PH_TARGET = "ph_target"
CONF_PH_TOLERANCE = "ph_tolerance"
CONF_CL_TARGET_MG_L = "cl_target_mg_l"
CONF_CL_TOLERANCE = "cl_tolerance"
CONF_ORP_MIN_MV = "orp_min_mv"
CONF_DOSE_MAX_PH_ML = "dose_max_ph_ml"
CONF_DOSE_MAX_CL_ML = "dose_max_cl_ml"
CONF_DELAY_BETWEEN_DOSES_MIN = "delay_between_doses_min"
CONF_DOSING_AUTO = "dosing_auto"
CONF_ENTITY_NOTIFY_PRIMARY = "entity_notify_primary"
CONF_ENTITY_NOTIFY_CRITICAL = "entity_notify_critical"

# Valeurs par defaut (profil)
DEFAULT_VOLUME_M3 = 16.0
DEFAULT_PH_MINUS_CONCENTRATION_PCT = 14.0
DEFAULT_DISINFECTANT_CONCENTRATION_PCT = 14.0

# Valeurs par defaut (entites systeme suggerees)
DEFAULT_ENTITY_SWITCH_FILTRATION = "switch.pool_pump"
DEFAULT_ENTITY_LEVEL_LOW = "binary_sensor.pool_level_low"
DEFAULT_ENTITY_WATER_TEMPERATURE = "sensor.pool_water_temperature_safe"
DEFAULT_ENTITY_SO_FILTRATION_DURATION = "input_number.pool_filtration_duration"
DEFAULT_ENTITY_SO_MAX_DURATION = "input_number.pool_filtration_max_min"

# Valeurs par defaut (sonde suggerees)
DEFAULT_ENTITY_PH = "sensor.pool_probe_ph"
DEFAULT_ENTITY_ORP = "sensor.pool_probe_orp"
DEFAULT_ENTITY_CL = "sensor.pool_probe_cl"
DEFAULT_ENTITY_TDS = "sensor.pool_probe_tds"
DEFAULT_ENTITY_SALINITY = "sensor.pool_probe_salinity"
DEFAULT_ENTITY_PROBE_TEMPERATURE = "sensor.pool_probe_temperature"

# Valeurs par defaut (pompes doseuses suggerees)
DEFAULT_ENTITY_SWITCH_PH = "switch.pool_dosing_pump_ph"
DEFAULT_ENTITY_SWITCH_CL = "switch.pool_dosing_pump_cl"
DEFAULT_ENTITY_NUMBER_PH_SPEED = "number.pool_dosing_pump_ph_speed"
DEFAULT_ENTITY_NUMBER_CL_SPEED = "number.pool_dosing_pump_cl_speed"
DEFAULT_FLOW_RATE_PH_ML_MIN = 30.0
DEFAULT_FLOW_RATE_CL_ML_MIN = 30.0

# Valeurs par defaut (consignes chimiques)
DEFAULT_PH_TARGET = 7.4
DEFAULT_PH_TOLERANCE = 0.2
DEFAULT_CL_TARGET_MG_L = 2.0
DEFAULT_CL_TOLERANCE = 0.5
DEFAULT_ORP_MIN_MV = 650
DEFAULT_DOSE_MAX_PH_ML = 100
DEFAULT_DOSE_MAX_CL_ML = 100
DEFAULT_DELAY_BETWEEN_DOSES_MIN = 60
DEFAULT_DOSING_AUTO = True
DEFAULT_ENTITY_NOTIFY_PRIMARY = "notify.mobile_app_owner"
DEFAULT_ENTITY_NOTIFY_CRITICAL = "notify.mobile_app_secondary"

# Options du type de traitement (etape 1)
TREATMENT_TYPES = [
    "chlore_liquide",
    "chlore_choc",
    "brome",
    "sel_electrolyse",
]

# Repli automatique pour la temperature eau si la sonde est vide
FALLBACK_WATER_TEMPERATURE = "sensor.pool_water_temperature_safe"

# Statuts chimiques normalises
STATUS_OK = "OK"
STATUS_HIGH = "HIGH"
STATUS_LOW = "LOW"
STATUS_CRITICAL = "CRITICAL"
STATUS_UNKNOWN = "UNKNOWN"

# Plateformes exposees a Home Assistant
PLATFORMS = ["sensor", "switch", "number", "select"]

# Noms des services HA
SERVICE_DOSE_PH = "dose_ph"
SERVICE_DOSE_CL = "dose_cl"
SERVICE_SET_FILTRATION_MODE = "set_filtration_mode"
SERVICE_RELOAD = "reload"

# Modes de filtration acceptes par le service set_filtration_mode
FILTRATION_MODES = ["auto", "force_on", "force_off", "winter"]
