"""Tests for the Sleeptracker API client."""

from __future__ import annotations

import base64

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.tempur_smartbase.api import (
    SleeptrackerApi,
    SleeptrackerAuthError,
    SleeptrackerError,
)
from custom_components.tempur_smartbase.const import Command

AUTH_URL = "https://auth.tsi.sleeptracker.com/v1/app/user/session"
CONTROL_URL = (
    "https://app.tsi.sleeptracker.com/actrack-client/v2/fpcsiot/processor/"
    "adjustableBaseControls"
)


async def test_login_and_command(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(
        AUTH_URL, json={"token": "tok", "expirationTimeSecs": 4102444800}
    )
    aioclient_mock.post(
        CONTROL_URL,
        json={
            "statusCode": 0,
            "statusMessage": "",
            "body": {"snapshots": [{"side": 0}]},
        },
    )
    api = SleeptrackerApi(async_get_clientsession(hass), "user@example.com", "pw")

    assert await api.send_command(Command.PRESET_FLAT) == [{"side": 0}]

    _, _, login_body, login_headers = aioclient_mock.mock_calls[0]
    expected = base64.b64encode(b"user@example.com:pw").decode()
    assert login_headers["Authorization"] == f"Basic {expected}"
    assert login_body["clientID"] == "sleeptracker-android-tsi"
    _, _, body, headers = aioclient_mock.mock_calls[1]
    assert headers["Authorization"] == "Bearer tok"
    assert body["bedControlCommand"] == 2

    # Token is reused while valid.
    await api.send_command(Command.STATUS)
    assert aioclient_mock.call_count == 3


async def test_bad_credentials(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(AUTH_URL, status=401)
    api = SleeptrackerApi(async_get_clientsession(hass), "user@example.com", "wrong")
    with pytest.raises(SleeptrackerAuthError):
        await api.authenticate()


async def test_command_error(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(
        AUTH_URL, json={"token": "tok", "expirationTimeSecs": 4102444800}
    )
    aioclient_mock.post(
        CONTROL_URL,
        json={"statusCode": 28, "statusMessage": "INVALID_PRESET", "body": {}},
    )
    api = SleeptrackerApi(async_get_clientsession(hass), "user@example.com", "pw")
    # Harmless for a status request, an error for a real command.
    assert await api.send_command(Command.STATUS) == []
    with pytest.raises(SleeptrackerError):
        await api.send_command(Command.PRESET_TV)
