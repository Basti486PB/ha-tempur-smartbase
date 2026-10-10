"""Motor covers (head, foot, tilt, lumbar) for the Tempur Smartbase."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityDescription,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import Command
from .coordinator import Bed, TempurConfigEntry, TempurCoordinator
from .entity import TempurEntity


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

    def __init__(
        self,
        coordinator: TempurCoordinator,
        bed: Bed,
        description: TempurCoverDescription,
    ) -> None:
        super().__init__(coordinator, bed, description.key)
        self.entity_description = description

    @property
    def is_closed(self) -> bool | None:
        state = self.bed_state
        if state is None or state.snapshot is None:
            return None
        motor = (state.snapshot.get(self.entity_description.snapshot_key) or {}).get(
            "motor"
        ) or {}
        pulses = motor.get("pulseCount")
        return None if pulses is None else pulses <= 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(self.entity_description.up)

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(self.entity_description.down)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(self.entity_description.stop)
