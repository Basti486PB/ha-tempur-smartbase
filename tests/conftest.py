"""Fixtures for the Tempur Smartbase tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

DEVICE = {
    "sleeptrackerProcessorID": 4242,
    "name": "Schlafzimmer",
    "active": True,
    "modelID": "ERGO-SMART",
    "processorSerialNumber": "SN123",
    "processorVersionFirmware": "1.2.3",
    "baseSmartCableSupported": True,
    "lastWiFiRSSI": -55,
    "powerBase": {
        "antiSnorePresetSupported": True,
        "headAngleTicksPerDegree": 10,
        "footAngleTicksPerDegree": 5,
    },
}

HELLO = {
    "productFeatures": ["motors", "env_sensors"],
    "productModel": "Sleeptracker AI",
    "motorMeta": {
        "capabilities": [
            {
                "side": 0,
                "motorRoster": {
                    "head": True,
                    "foot": True,
                    "headTilt": False,
                    "lumber": True,
                },
                "massageRoster": {"head": True, "foot": True},
            },
            {
                "side": 1,
                "motorRoster": {
                    "head": True,
                    "foot": True,
                    "headTilt": False,
                    "lumber": False,
                },
                "massageRoster": {"head": False, "foot": False},
            },
        ]
    },
}

SENSOR_MAP = [
    {"unitNumber": 0, "self": True, "userFirstName": "Basti"},
    {"unitNumber": 1, "self": False, "userFirstName": "Partner"},
]

SNAPSHOTS = [
    {
        "side": 0,
        "head": {
            "motor": {"pulseCount": 300},
            "massage": {"active": True, "strength": 4},
        },
        "foot": {
            "motor": {"pulseCount": 0},
            "massage": {"active": False, "strength": 0},
        },
        "lumbar": {
            "motor": {"pulseCount": 0},
            "massage": {"active": False, "strength": 0},
        },
        "massagePattern": 3,
        "massageTimerMins": 10,
        "massageTimerSecs": 30,
        "safetyLightOn": False,
    },
    {"side": 1, "head": {"motor": {"pulseCount": 0}}, "safetyLightOn": True},
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_api():
    with (
        patch(
            "custom_components.tempur_smartbase.SleeptrackerApi", autospec=True
        ) as api_cls,
        patch(
            "custom_components.tempur_smartbase.config_flow.SleeptrackerApi",
            new=api_cls,
        ),
    ):
        api = api_cls.return_value
        api.authenticate = AsyncMock()
        api.get_devices = AsyncMock(return_value=[DEVICE])
        api.get_hello = AsyncMock(return_value=HELLO)
        api.get_sensor_map = AsyncMock(return_value=SENSOR_MAP)
        api.get_environment = AsyncMock(
            return_value={"degreesCelsius": 21.5, "humidityPercentage": 45.0}
        )
        api.get_snore_relief = AsyncMock(
            return_value={"snoreReliefTilt": True, "snoreReliefVibration": False}
        )
        api.set_snore_relief = AsyncMock()
        api.send_command = AsyncMock(return_value=SNAPSHOTS)
        yield api
