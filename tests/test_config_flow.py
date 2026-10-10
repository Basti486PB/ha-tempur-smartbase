"""Config flow tests."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.tempur_smartbase.api import (
    SleeptrackerAuthError,
    SleeptrackerConnectionError,
)
from custom_components.tempur_smartbase.const import CONF_BRAND, DOMAIN

USER_INPUT = {CONF_EMAIL: " A@B.de ", CONF_PASSWORD: "pw", CONF_BRAND: "tempur"}


async def test_user_flow(hass: HomeAssistant, mock_api) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "a@b.de"
    assert result["data"] == {
        CONF_EMAIL: "a@b.de",
        CONF_PASSWORD: "pw",
        CONF_BRAND: "tempur",
    }


async def test_user_flow_errors(hass: HomeAssistant, mock_api) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    mock_api.authenticate.side_effect = SleeptrackerAuthError
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["errors"] == {"base": "invalid_auth"}

    mock_api.authenticate.side_effect = SleeptrackerConnectionError
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["errors"] == {"base": "cannot_connect"}

    mock_api.authenticate.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
