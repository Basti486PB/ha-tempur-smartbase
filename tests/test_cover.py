"""Tests for continuous motor movement."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tempur_smartbase.const import CONF_BRAND, DOMAIN, Command

from .conftest import SNAPSHOTS


async def _setup(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="tempur_user@example.com",
        data={
            CONF_EMAIL: "user@example.com",
            CONF_PASSWORD: "pw",
            CONF_BRAND: "tempur",
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _snapshots(head_pulses: int) -> list[dict]:
    own = {**SNAPSHOTS[0], "head": {"motor": {"pulseCount": head_pulses}}}
    return [own, SNAPSHOTS[1]]


def _count(mock_api, command: Command) -> int:
    return sum(1 for c in mock_api.send_command.call_args_list if c.args[0] == command)


@patch("custom_components.tempur_smartbase.cover.MIN_COMMAND_INTERVAL", 0)
async def test_move_repeats_until_end_stop(hass: HomeAssistant, mock_api) -> None:
    await _setup(hass)
    positions = iter([10, 20, 30, 40, 50] + [50] * 20)

    async def send(command, **_):
        if command == Command.MOTOR_HEAD_UP:
            return _snapshots(next(positions))
        return SNAPSHOTS

    mock_api.send_command.side_effect = send
    await hass.services.async_call(
        "cover", "open_cover", {"entity_id": "cover.schlafzimmer_head"}, blocking=True
    )
    await hass.async_block_till_done(wait_background_tasks=True)

    # 5 moving steps, then 4 unchanged readings at the end stop.
    assert _count(mock_api, Command.MOTOR_HEAD_UP) == 9
    assert hass.states.get("cover.schlafzimmer_head").state == "open"


@patch("custom_components.tempur_smartbase.cover.MIN_COMMAND_INTERVAL", 0.01)
async def test_stop_cancels_move(hass: HomeAssistant, mock_api) -> None:
    await _setup(hass)
    await hass.services.async_call(
        "cover", "close_cover", {"entity_id": "cover.schlafzimmer_head"}, blocking=True
    )
    await asyncio.sleep(0.05)
    assert hass.states.get("cover.schlafzimmer_head").state == "closing"
    sent_before_stop = _count(mock_api, Command.MOTOR_HEAD_DOWN)
    assert sent_before_stop > 1

    await hass.services.async_call(
        "cover", "stop_cover", {"entity_id": "cover.schlafzimmer_head"}, blocking=True
    )
    await asyncio.sleep(0.05)
    assert _count(mock_api, Command.MOTOR_HEAD_DOWN) == sent_before_stop
    mock_api.send_command.assert_any_call(Command.MOTOR_HEAD_STOP)
    assert hass.states.get("cover.schlafzimmer_head").state != "closing"


@patch("custom_components.tempur_smartbase.cover.MIN_COMMAND_INTERVAL", 0)
@patch("custom_components.tempur_smartbase.cover.MAX_MOVE_SECONDS", 0.05)
async def test_move_without_position_stops_at_time_limit(
    hass: HomeAssistant, mock_api
) -> None:
    await _setup(hass)
    await hass.services.async_call(
        "cover", "open_cover", {"entity_id": "cover.schlafzimmer_lumbar"}, blocking=True
    )
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()
    assert _count(mock_api, Command.MOTOR_LUMBAR_UP) > 1
    assert hass.states.get("cover.schlafzimmer_lumbar").state != "opening"
