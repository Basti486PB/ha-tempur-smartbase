"""Setup, entity and command tests."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tempur_smartbase.api import SleeptrackerAuthError
from custom_components.tempur_smartbase.const import CONF_BRAND, DOMAIN, Command


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="tempur_user@example.com",
        data={
            CONF_EMAIL: "user@example.com",
            CONF_PASSWORD: "pw",
            CONF_BRAND: "tempur",
        },
    )


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = _entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_setup_creates_entities(hass: HomeAssistant, mock_api) -> None:
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED

    assert hass.states.get("sensor.schlafzimmer_head_angle").state == "30.0"
    assert hass.states.get("sensor.schlafzimmer_foot_angle").state == "0.0"
    assert hass.states.get("sensor.schlafzimmer_massage_pattern").state == "ripple"
    assert hass.states.get("sensor.schlafzimmer_massage_time_remaining").state == "10.5"
    assert hass.states.get("sensor.schlafzimmer_temperature").state == "21.5"
    assert hass.states.get("sensor.schlafzimmer_co2").state == "unknown"
    assert hass.states.get("cover.schlafzimmer_head").state == "open"
    assert hass.states.get("cover.schlafzimmer_foot").state == "closed"
    assert hass.states.get("cover.schlafzimmer_lumbar") is not None
    assert hass.states.get("cover.schlafzimmer_head_tilt") is None
    assert hass.states.get("switch.schlafzimmer_safety_light").state == "off"
    assert hass.states.get("switch.schlafzimmer_snore_relief_tilt").state == "on"
    assert hass.states.get("button.schlafzimmer_preset_anti_snore") is not None
    assert hass.states.get("button.schlafzimmer_head_massage_step") is not None


async def test_commands(hass: HomeAssistant, mock_api) -> None:
    await _setup(hass)

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.schlafzimmer_preset_flat"},
        blocking=True,
    )
    mock_api.send_command.assert_any_call(Command.PRESET_FLAT)

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.schlafzimmer_head_massage_step"},
        blocking=True,
    )
    mock_api.send_command.assert_any_call(
        Command.MASSAGE_HEAD_STEP, massageAdjustment=1, requestStatus=True
    )

    await hass.services.async_call(
        "cover", "open_cover", {"entity_id": "cover.schlafzimmer_head"}, blocking=True
    )
    mock_api.send_command.assert_any_call(Command.MOTOR_HEAD_UP)
    await hass.services.async_call(
        "cover", "stop_cover", {"entity_id": "cover.schlafzimmer_head"}, blocking=True
    )
    mock_api.send_command.assert_any_call(Command.MOTOR_HEAD_STOP)

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.schlafzimmer_safety_light"},
        blocking=True,
    )
    mock_api.send_command.assert_any_call(Command.TOGGLE_SAFETY_LIGHTS)

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.schlafzimmer_snore_relief_vibration"},
        blocking=True,
    )
    mock_api.set_snore_relief.assert_called_once_with(tilt=True, vibration=True)


async def test_auth_failure_starts_reauth(hass: HomeAssistant, mock_api) -> None:
    mock_api.get_devices.side_effect = SleeptrackerAuthError("nope")
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert any(f["context"]["source"] == "reauth" for f in flows)
