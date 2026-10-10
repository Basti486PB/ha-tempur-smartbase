"""Switches for the Tempur Smartbase."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import Command
from .coordinator import Bed, TempurConfigEntry, TempurCoordinator
from .entity import TempurEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TempurConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SwitchEntity] = []
    for bed in coordinator.beds.values():
        if not bed.has_base_controls:
            continue
        entities.append(SafetyLightSwitch(coordinator, bed))
        for key, field in (
            ("snore_relief_tilt", "snoreReliefTilt"),
            ("snore_relief_vibration", "snoreReliefVibration"),
        ):
            entities.append(SnoreReliefSwitch(coordinator, bed, key, field))
    async_add_entities(entities)


class SafetyLightSwitch(TempurEntity, SwitchEntity):
    """Under-bed safety light. The base only offers a toggle command."""

    def __init__(self, coordinator: TempurCoordinator, bed: Bed) -> None:
        super().__init__(coordinator, bed, "safety_light")

    @property
    def is_on(self) -> bool | None:
        state = self.bed_state
        if state is None or state.snapshot is None:
            return None
        value = state.snapshot.get("safetyLightOn")
        return None if value is None else bool(value)

    async def _async_set(self, on: bool) -> None:
        if self.is_on is not on:
            await self.coordinator.async_send_command(Command.TOGGLE_SAFETY_LIGHTS)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set(False)


class SnoreReliefSwitch(TempurEntity, SwitchEntity):
    """Automatic snore relief setting of the account (tilt or vibration)."""

    def __init__(
        self, coordinator: TempurCoordinator, bed: Bed, key: str, field: str
    ) -> None:
        super().__init__(coordinator, bed, key)
        self._field = field

    @property
    def available(self) -> bool:
        data = self.coordinator.data
        return super().available and data is not None and data.snore_relief is not None

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if data is None or data.snore_relief is None:
            return None
        return data.snore_relief.get(self._field)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_snore_relief(**{self._field: True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_snore_relief(**{self._field: False})
