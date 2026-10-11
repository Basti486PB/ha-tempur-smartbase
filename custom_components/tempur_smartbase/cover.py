"""Motor covers (head, foot, tilt, lumbar) for the Tempur Smartbase."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityDescription,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import Command
from .coordinator import Bed, TempurConfigEntry, TempurCoordinator
from .entity import TempurEntity

_LOGGER = logging.getLogger(__name__)

# The base treats each motor command like a short press on the remote, so a
# move is repeated until it is stopped, the motor stops changing position, or
# this safety limit is reached.
MAX_MOVE_SECONDS = 45
MIN_COMMAND_INTERVAL = 0.5
STALL_REPEATS = 4


@dataclass(frozen=True, kw_only=True)
class TempurCoverDescription(CoverEntityDescription):
    """Describes one motor of the base."""

    roster_key: str
    snapshot_key: str
    up: Command
    down: Command
    stop: Command


COVERS: tuple[TempurCoverDescription, ...] = (
    TempurCoverDescription(
        key="motor_head",
        roster_key="head",
        snapshot_key="head",
        up=Command.MOTOR_HEAD_UP,
        down=Command.MOTOR_HEAD_DOWN,
        stop=Command.MOTOR_HEAD_STOP,
    ),
    TempurCoverDescription(
        key="motor_foot",
        roster_key="foot",
        snapshot_key="foot",
        up=Command.MOTOR_FEET_UP,
        down=Command.MOTOR_FEET_DOWN,
        stop=Command.MOTOR_FEET_STOP,
    ),
    TempurCoverDescription(
        key="motor_tilt",
        roster_key="headTilt",
        snapshot_key="headTilt",
        up=Command.MOTOR_TILT_UP,
        down=Command.MOTOR_TILT_DOWN,
        stop=Command.MOTOR_TILT_STOP,
    ),
    TempurCoverDescription(
        key="motor_lumbar",
        # The cloud spells it "lumber" in the capability roster.
        roster_key="lumber",
        snapshot_key="lumbar",
        up=Command.MOTOR_LUMBAR_UP,
        down=Command.MOTOR_LUMBAR_DOWN,
        stop=Command.MOTOR_LUMBAR_STOP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TempurConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        TempurMotorCover(coordinator, bed, description)
        for bed in coordinator.beds.values()
        if bed.has_motors
        for description in COVERS
        if bed.motor_roster.get(description.roster_key)
    )


class TempurMotorCover(TempurEntity, CoverEntity):
    """One motor: open raises it, close lowers it, stop halts it."""

    entity_description: TempurCoverDescription
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )
    # Keep both directions usable in the UI whatever the reported position.
    _attr_assumed_state = True

    def __init__(
        self,
        coordinator: TempurCoordinator,
        bed: Bed,
        description: TempurCoverDescription,
    ) -> None:
        super().__init__(coordinator, bed, description.key)
        self.entity_description = description
        self._move_task: asyncio.Task[None] | None = None
        self._moving: Command | None = None

    def _pulses(self, snapshot: dict[str, Any] | None) -> int | None:
        if snapshot is None:
            return None
        motor = (snapshot.get(self.entity_description.snapshot_key) or {}).get(
            "motor"
        ) or {}
        return motor.get("pulseCount")

    @property
    def is_closed(self) -> bool | None:
        state = self.bed_state
        pulses = self._pulses(state.snapshot if state else None)
        return None if pulses is None else pulses <= 0

    @property
    def is_opening(self) -> bool:
        return self._moving == self.entity_description.up

    @property
    def is_closing(self) -> bool:
        return self._moving == self.entity_description.down

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._async_start_move(self.entity_description.up)

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._async_start_move(self.entity_description.down)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self._async_cancel_move()
        await self.coordinator.async_send_command(self.entity_description.stop)

    async def async_will_remove_from_hass(self) -> None:
        await self._async_cancel_move()

    async def _async_start_move(self, command: Command) -> None:
        await self._async_cancel_move()
        # Send the first step right away so errors reach the caller.
        snapshots = await self.coordinator.async_send_command_raw(command)
        self._moving = command
        self.async_write_ha_state()
        self._move_task = self.coordinator.config_entry.async_create_background_task(
            self.hass,
            self._async_keep_moving(command, self._own_pulses(snapshots)),
            f"{self.entity_id} move",
        )

    async def _async_cancel_move(self) -> None:
        task, self._move_task = self._move_task, None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    def _own_pulses(self, snapshots: list[dict[str, Any]]) -> int | None:
        own = next((s for s in snapshots if s.get("side") == self.bed.side), None)
        return self._pulses(own)

    async def _async_keep_moving(self, command: Command, last: int | None) -> None:
        deadline = time.monotonic() + MAX_MOVE_SECONDS
        moved = False
        unchanged = 0
        try:
            while time.monotonic() < deadline:
                started = time.monotonic()
                snapshots = await self.coordinator.async_send_command_raw(command)
                pulses = self._own_pulses(snapshots)
                if pulses is not None and last is not None and pulses != last:
                    moved = True
                    unchanged = 0
                elif moved:
                    # Only motors that report a position can be seen stalling
                    # at their end stop.
                    unchanged += 1
                    if unchanged >= STALL_REPEATS:
                        break
                last = pulses
                await asyncio.sleep(
                    max(0, MIN_COMMAND_INTERVAL - (time.monotonic() - started))
                )
        except HomeAssistantError as err:
            _LOGGER.warning("Stopped moving %s: %s", self.entity_id, err)
        finally:
            self._moving = None
            self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
