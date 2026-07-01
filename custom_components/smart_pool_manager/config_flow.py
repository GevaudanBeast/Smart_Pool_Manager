"""Config flow UI pour SmartPoolManager.

Definit l'assistant de configuration en 5 etapes (profil, sonde, pompes
doseuses, entites systeme, consignes chimiques) ainsi que l'OptionsFlow qui
permet de modifier uniquement les consignes (etape 5) sans retoucher les
entites configurees aux etapes 2 a 4.

Toute la validation passe par voluptuous. Les libelles des champs sont
fournis par translations/fr.json et translations/en.json.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_CL_TARGET_MG_L,
    CONF_CL_TOLERANCE,
    CONF_DELAY_BETWEEN_DOSES_MIN,
    CONF_DISINFECTANT_CONCENTRATION_PCT,
    CONF_DOSE_MAX_CL_ML,
    CONF_DOSE_MAX_PH_ML,
    CONF_DOSING_AUTO,
    CONF_ENTITY_CL,
    CONF_ENTITY_LEVEL_LOW,
    CONF_ENTITY_NOTIFY_CRITICAL,
    CONF_ENTITY_NOTIFY_PRIMARY,
    CONF_ENTITY_NUMBER_CL_SPEED,
    CONF_ENTITY_NUMBER_PH_SPEED,
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
    CONF_RECO_CL_MAX,
    CONF_RECO_CL_MIN,
    CONF_RECO_CL_SHOCK,
    CONF_RECO_DOSE_CHOC_G,
    CONF_RECO_DOSE_PH_MINUS_G,
    CONF_RECO_DOSE_PH_PLUS_G,
    CONF_RECO_GALET_G,
    CONF_RECO_NOTIFY_SERVICE,
    CONF_RECO_PH_IDEAL_MAX,
    CONF_RECO_PH_IDEAL_MIN,
    CONF_RECO_PH_TARGET,
    CONF_RECO_REF_VOLUME_M3,
    CONF_TREATMENT_TYPE,
    CONF_VOLUME_M3,
    DEFAULT_CL_TARGET_MG_L,
    DEFAULT_CL_TOLERANCE,
    DEFAULT_DELAY_BETWEEN_DOSES_MIN,
    DEFAULT_DOSE_MAX_CL_ML,
    DEFAULT_DOSE_MAX_PH_ML,
    DEFAULT_DOSING_AUTO,
    DEFAULT_ENTITY_NOTIFY_CRITICAL,
    DEFAULT_ENTITY_NOTIFY_PRIMARY,
    DEFAULT_FLOW_RATE_CL_ML_MIN,
    DEFAULT_FLOW_RATE_PH_ML_MIN,
    DEFAULT_ORP_MIN_MV,
    DEFAULT_PH_MINUS_CONCENTRATION_PCT,
    DEFAULT_PH_TARGET,
    DEFAULT_PH_TOLERANCE,
    DEFAULT_RECO_CL_MAX,
    DEFAULT_RECO_CL_MIN,
    DEFAULT_RECO_CL_SHOCK,
    DEFAULT_RECO_DOSE_CHOC_G,
    DEFAULT_RECO_DOSE_PH_MINUS_G,
    DEFAULT_RECO_DOSE_PH_PLUS_G,
    DEFAULT_RECO_GALET_G,
    DEFAULT_RECO_NOTIFY_SERVICE,
    DEFAULT_RECO_PH_IDEAL_MAX,
    DEFAULT_RECO_PH_IDEAL_MIN,
    DEFAULT_RECO_PH_TARGET,
    DEFAULT_RECO_REF_VOLUME_M3,
    DEFAULT_VOLUME_M3,
    DOMAIN,
    TREATMENT_TYPES,
)
from .const import (
    DEFAULT_DISINFECTANT_CONCENTRATION_PCT as _DISINF_DEFAULT,
)


def _step5_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Construit le schema de l'etape 5 (consignes chimiques).

    Partage entre le ConfigFlow et l'OptionsFlow pour rester coherent.
    Les valeurs par defaut sont injectees depuis defaults.
    """
    return vol.Schema(
        {
            vol.Required(
                CONF_PH_TARGET, default=defaults.get(CONF_PH_TARGET, DEFAULT_PH_TARGET)
            ): NumberSelector(
                NumberSelectorConfig(
                    min=7.0, max=7.8, step=0.05, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_PH_TOLERANCE,
                default=defaults.get(CONF_PH_TOLERANCE, DEFAULT_PH_TOLERANCE),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.0, max=0.5, step=0.05, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_CL_TARGET_MG_L,
                default=defaults.get(CONF_CL_TARGET_MG_L, DEFAULT_CL_TARGET_MG_L),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.5, max=5.0, step=0.1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_CL_TOLERANCE,
                default=defaults.get(CONF_CL_TOLERANCE, DEFAULT_CL_TOLERANCE),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.0, max=1.0, step=0.1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_ORP_MIN_MV,
                default=defaults.get(CONF_ORP_MIN_MV, DEFAULT_ORP_MIN_MV),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=400, max=800, step=1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_DOSE_MAX_PH_ML,
                default=defaults.get(CONF_DOSE_MAX_PH_ML, DEFAULT_DOSE_MAX_PH_ML),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=10, max=500, step=1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_DOSE_MAX_CL_ML,
                default=defaults.get(CONF_DOSE_MAX_CL_ML, DEFAULT_DOSE_MAX_CL_ML),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=10, max=500, step=1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_DELAY_BETWEEN_DOSES_MIN,
                default=defaults.get(
                    CONF_DELAY_BETWEEN_DOSES_MIN, DEFAULT_DELAY_BETWEEN_DOSES_MIN
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=30, max=480, step=1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_DOSING_AUTO,
                default=defaults.get(CONF_DOSING_AUTO, DEFAULT_DOSING_AUTO),
            ): BooleanSelector(),
            vol.Required(
                CONF_ENTITY_NOTIFY_PRIMARY,
                default=defaults.get(
                    CONF_ENTITY_NOTIFY_PRIMARY, DEFAULT_ENTITY_NOTIFY_PRIMARY
                ),
            ): TextSelector(),
            vol.Required(
                CONF_ENTITY_NOTIFY_CRITICAL,
                default=defaults.get(
                    CONF_ENTITY_NOTIFY_CRITICAL, DEFAULT_ENTITY_NOTIFY_CRITICAL
                ),
            ): TextSelector(),
        }
    )


def _reco_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Construit le schema de l'etape recommandations manuelles (etape 6).

    Regroupe les cibles dediees au conseil manuel, les doses unitaires des
    produits en grammes et le service de notification cible. Partage entre le
    ConfigFlow et l'OptionsFlow.
    """
    return vol.Schema(
        {
            vol.Required(
                CONF_RECO_PH_TARGET,
                default=defaults.get(CONF_RECO_PH_TARGET, DEFAULT_RECO_PH_TARGET),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=6.8, max=7.6, step=0.05, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_RECO_PH_IDEAL_MIN,
                default=defaults.get(CONF_RECO_PH_IDEAL_MIN, DEFAULT_RECO_PH_IDEAL_MIN),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=6.5, max=7.4, step=0.05, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_RECO_PH_IDEAL_MAX,
                default=defaults.get(CONF_RECO_PH_IDEAL_MAX, DEFAULT_RECO_PH_IDEAL_MAX),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=7.0, max=7.8, step=0.05, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_RECO_CL_MIN,
                default=defaults.get(CONF_RECO_CL_MIN, DEFAULT_RECO_CL_MIN),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.1, max=3.0, step=0.1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_RECO_CL_MAX,
                default=defaults.get(CONF_RECO_CL_MAX, DEFAULT_RECO_CL_MAX),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1.0, max=6.0, step=0.1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_RECO_CL_SHOCK,
                default=defaults.get(CONF_RECO_CL_SHOCK, DEFAULT_RECO_CL_SHOCK),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.0, max=2.0, step=0.1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_RECO_DOSE_PH_MINUS_G,
                default=defaults.get(
                    CONF_RECO_DOSE_PH_MINUS_G, DEFAULT_RECO_DOSE_PH_MINUS_G
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=10, max=1000, step=10, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_RECO_DOSE_PH_PLUS_G,
                default=defaults.get(
                    CONF_RECO_DOSE_PH_PLUS_G, DEFAULT_RECO_DOSE_PH_PLUS_G
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=10, max=1000, step=10, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_RECO_DOSE_CHOC_G,
                default=defaults.get(CONF_RECO_DOSE_CHOC_G, DEFAULT_RECO_DOSE_CHOC_G),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=10, max=2000, step=10, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_RECO_GALET_G,
                default=defaults.get(CONF_RECO_GALET_G, DEFAULT_RECO_GALET_G),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=50, max=500, step=10, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_RECO_REF_VOLUME_M3,
                default=defaults.get(
                    CONF_RECO_REF_VOLUME_M3, DEFAULT_RECO_REF_VOLUME_M3
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1.0, max=500.0, step=0.5, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_RECO_NOTIFY_SERVICE,
                default=defaults.get(
                    CONF_RECO_NOTIFY_SERVICE, DEFAULT_RECO_NOTIFY_SERVICE
                ),
            ): TextSelector(),
        }
    )


class SmartPoolConfigFlow(ConfigFlow, domain=DOMAIN):
    """Assistant de configuration UI en 6 etapes."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise l'accumulateur de donnees entre les etapes."""
        self._data: dict[str, Any] = {}

    # ----- Etape 1 : profil piscine -----
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        """Premiere etape : profil de la piscine."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_probe()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Ma piscine"): TextSelector(),
                vol.Required(CONF_VOLUME_M3, default=DEFAULT_VOLUME_M3): NumberSelector(
                    NumberSelectorConfig(
                        min=1.0, max=500.0, step=0.5, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_TREATMENT_TYPE, default=TREATMENT_TYPES[0]
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=TREATMENT_TYPES,
                        translation_key=CONF_TREATMENT_TYPE,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_PH_MINUS_CONCENTRATION_PCT,
                    default=DEFAULT_PH_MINUS_CONCENTRATION_PCT,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5, max=35, step=0.5, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_DISINFECTANT_CONCENTRATION_PCT,
                    default=_DISINF_DEFAULT,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5, max=20, step=0.5, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    # ----- Etape 2 : entites sonde -----
    async def async_step_probe(self, user_input: dict[str, Any] | None = None) -> Any:
        """Deuxieme etape : entites de la sonde Zigbee."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_dosing()

        sensor_sel = EntitySelector(EntitySelectorConfig(domain="sensor"))
        schema = vol.Schema(
            {
                vol.Required(CONF_ENTITY_PH): sensor_sel,
                vol.Required(CONF_ENTITY_ORP): sensor_sel,
                vol.Required(CONF_ENTITY_CL): sensor_sel,
                vol.Optional(CONF_ENTITY_TDS): sensor_sel,
                vol.Optional(CONF_ENTITY_SALINITY): sensor_sel,
                vol.Optional(CONF_ENTITY_PROBE_TEMPERATURE): sensor_sel,
            }
        )
        return self.async_show_form(step_id="probe", data_schema=schema)

    # ----- Etape 3 : pompes doseuses -----
    async def async_step_dosing(self, user_input: dict[str, Any] | None = None) -> Any:
        """Troisieme etape : pompes doseuses ESPHome."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_system()

        switch_sel = EntitySelector(EntitySelectorConfig(domain="switch"))
        number_sel = EntitySelector(EntitySelectorConfig(domain="number"))
        # Les pompes doseuses sont facultatives : un utilisateur qui dose a la
        # main (mode conseil seul) laisse ces champs vides.
        schema = vol.Schema(
            {
                vol.Optional(CONF_ENTITY_SWITCH_PH): switch_sel,
                vol.Optional(CONF_ENTITY_SWITCH_CL): switch_sel,
                vol.Optional(CONF_ENTITY_NUMBER_PH_SPEED): number_sel,
                vol.Optional(CONF_ENTITY_NUMBER_CL_SPEED): number_sel,
                vol.Required(
                    CONF_FLOW_RATE_PH_ML_MIN, default=DEFAULT_FLOW_RATE_PH_ML_MIN
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=200, step=0.5, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_FLOW_RATE_CL_ML_MIN, default=DEFAULT_FLOW_RATE_CL_ML_MIN
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=200, step=0.5, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(step_id="dosing", data_schema=schema)

    # ----- Etape 4 : entites systeme -----
    async def async_step_system(self, user_input: dict[str, Any] | None = None) -> Any:
        """Quatrieme etape : entites systeme et interface Solar Optimizer."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_chemistry()

        # Toutes ces entites sont facultatives : elles ne concernent que le
        # mode automatique et l'interface Solar Optimizer. En mode conseil
        # seul, on laisse vides celles dont on ne dispose pas. Le capteur de
        # temperature reste utile pour la filtration conseillee, mais peut etre
        # fourni par la sonde (etape 2).
        schema = vol.Schema(
            {
                vol.Optional(CONF_ENTITY_SWITCH_FILTRATION): EntitySelector(
                    EntitySelectorConfig(domain="switch")
                ),
                vol.Optional(CONF_ENTITY_LEVEL_LOW): EntitySelector(
                    EntitySelectorConfig(domain="binary_sensor")
                ),
                vol.Optional(CONF_ENTITY_WATER_TEMPERATURE): EntitySelector(
                    EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_ENTITY_SO_FILTRATION_DURATION): EntitySelector(
                    EntitySelectorConfig(domain="input_number")
                ),
                vol.Optional(CONF_ENTITY_SO_MAX_DURATION): EntitySelector(
                    EntitySelectorConfig(domain="input_number")
                ),
            }
        )
        return self.async_show_form(step_id="system", data_schema=schema)

    # ----- Etape 5 : consignes chimiques -----
    async def async_step_chemistry(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Cinquieme etape : consignes chimiques (modifiables via options)."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_reco()

        return self.async_show_form(step_id="chemistry", data_schema=_step5_schema({}))

    # ----- Etape 6 : recommandations manuelles -----
    async def async_step_reco(self, user_input: dict[str, Any] | None = None) -> Any:
        """Sixieme etape : conseil manuel en grammes et service de notification."""
        if user_input is not None:
            self._data.update(user_input)
            await self.async_set_unique_id(self._data[CONF_NAME])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)

        return self.async_show_form(step_id="reco", data_schema=_reco_schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Retourne l'OptionsFlow associe."""
        return SmartPoolOptionsFlow(config_entry)


class SmartPoolOptionsFlow(OptionsFlow):
    """OptionsFlow : modifie uniquement les consignes chimiques (etape 5).

    Les entites configurees aux etapes 2 a 4 ne sont pas touchees.
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Conserve l'entree pour pre-remplir les valeurs courantes."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        """Menu de choix : consignes chimiques ou recommandations manuelles."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["chemistry", "reco"],
        )

    async def async_step_chemistry(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Modifie les consignes chimiques (dosage auto)."""
        if user_input is not None:
            data = {**self.config_entry.options, **user_input}
            return self.async_create_entry(title="", data=data)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="chemistry", data_schema=_step5_schema(defaults)
        )

    async def async_step_reco(self, user_input: dict[str, Any] | None = None) -> Any:
        """Modifie les reglages des recommandations manuelles."""
        if user_input is not None:
            data = {**self.config_entry.options, **user_input}
            return self.async_create_entry(title="", data=data)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="reco", data_schema=_reco_schema(defaults))
