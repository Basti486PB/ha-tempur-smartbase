"""Config flow for the Tempur Smartbase integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    SleeptrackerApi,
    SleeptrackerAuthError,
    SleeptrackerConnectionError,
    SleeptrackerError,
)
from .const import BRAND_CONFIG, BRAND_TEMPUR, CONF_BRAND, DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
        vol.Required(CONF_BRAND, default=BRAND_TEMPUR): SelectSelector(
            SelectSelectorConfig(
                options=list(BRAND_CONFIG),
                mode=SelectSelectorMode.DROPDOWN,
                translation_key=CONF_BRAND,
            )
        ),
    }
)

REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
    }
)


class TempurSmartbaseConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for a Sleeptracker account."""

    VERSION = 1

    async def _async_validate(
        self, email: str, password: str, brand: str
    ) -> dict[str, str]:
        api = SleeptrackerApi(
            async_get_clientsession(self.hass), email, password, brand
        )
        try:
            await api.authenticate()
            await api.get_devices()
        except SleeptrackerAuthError:
            return {"base": "invalid_auth"}
        except SleeptrackerConnectionError:
            return {"base": "cannot_connect"}
        except SleeptrackerError:
            _LOGGER.exception("Unexpected response from the Sleeptracker cloud")
            return {"base": "unknown"}
        return {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            brand = user_input[CONF_BRAND]
            await self.async_set_unique_id(f"{brand}_{email}")
            self._abort_if_unique_id_configured()
            errors = await self._async_validate(email, user_input[CONF_PASSWORD], brand)
            if not errors:
                return self.async_create_entry(
                    title=email,
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_BRAND: brand,
                    },
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await self._async_validate(
                entry.data[CONF_EMAIL],
                user_input[CONF_PASSWORD],
                entry.data.get(CONF_BRAND, BRAND_TEMPUR),
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            description_placeholders={"email": entry.data[CONF_EMAIL]},
            errors=errors,
        )
