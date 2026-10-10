"""Preset, program and massage buttons for the Tempur Smartbase."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import Command
from .coordinator import Bed, TempurConfigEntry, TempurCoordinator
from .entity import TempurEntity


@dataclass(frozen=True, kw_only=True)
class TempurButtonDescription(ButtonEntityDescription):
    """Describes a button that sends one base command."""

    command: Command
    payload: dict[str, Any] = field(default_factory=dict)
    supported: Callable[[Bed], bool] = lambda bed: True


def _massage(*zones: str, any_zone: bool = False) -> Callable[[Bed], bool]:
    check = any if any_zone else all
    return lambda bed: check(bed.massage_roster.get(z) for z in zones)


BUTTONS: tuple[TempurButtonDescription, ...] = (
    TempurButtonDescription(key="preset_flat", command=Command.PRESET_FLAT),
    TempurButtonDescription(key="preset_zero_g", command=Command.PRESET_ZERO_G),
    TempurButtonDescription(key="preset_tv", command=Command.PRESET_TV),
    TempurButtonDescription(
        key="preset_user_favorite", command=Command.PRESET_USER_FAVORITE
    ),
    TempurButtonDescription(
        key="preset_anti_snore",
        command=Command.PRESET_ANTI_SNORE,
        supported=lambda bed: bed.anti_snore_supported,
    ),
    TempurButtonDescription(
        key="program_zero_g",
        command=Command.PROGRAM_ZERO_G,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    TempurButtonDescription(
        key="program_tv",
        command=Command.PROGRAM_TV,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    TempurButtonDescription(
        key="program_user_favorite",
        command=Command.PROGRAM_USER_FAVORITE,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    TempurButtonDescription(
        key="program_anti_snore",
        command=Command.PROGRAM_ANTI_SNORE,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        supported=lambda bed: bed.anti_snore_supported,
    ),
    TempurButtonDescription(
        key="massage_head_step",
        command=Command.MASSAGE_HEAD_STEP,
        payload={"massageAdjustment": 1, "requestStatus": True},
        supported=_massage("head"),
    ),
    TempurButtonDescription(
        key="massage_foot_step",
        command=Command.MASSAGE_FOOT_STEP,
        payload={"massageAdjustment": 1, "requestStatus": True},
        supported=_massage("foot"),
    ),
    TempurButtonDescription(
        key="massage_step",
        command=Command.MASSAGE_STEP,
        supported=_massage("head", "foot"),
    ),
    TempurButtonDescription(
        key="massage_pattern_step",
        command=Command.MASSAGE_PATTERN_STEP,
        supported=_massage("head", "foot", any_zone=True),
    ),
    TempurButtonDescription(
        key="massage_timer_step",
        command=Command.MASSAGE_TIMER_STEP,
        supported=_massage("head", "foot", any_zone=True),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TempurConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        TempurButton(coordinator, bed, description)
        for bed in coordinator.beds.values()
        if bed.has_base_controls
        for description in BUTTONS
        if description.supported(bed)
    )


class TempurButton(TempurEntity, ButtonEntity):
    """Sends a single command to the base."""

    entity_description: TempurButtonDescription

    def __init__(
        self,
        coordinator: TempurCoordinator,
        bed: Bed,
        description: TempurButtonDescription,
    ) -> None:
        super().__init__(coordinator, bed, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(
            self.entity_description.command, **self.entity_description.payload
        )
