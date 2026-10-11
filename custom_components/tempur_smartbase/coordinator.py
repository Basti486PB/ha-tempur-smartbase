"""Data coordinator for the Tempur Smartbase integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SleeptrackerApi, SleeptrackerAuthError, SleeptrackerError
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FEATURE_ENV_SENSORS,
    FEATURE_MOTORS,
    Command,
)

_LOGGER = logging.getLogger(__name__)

type TempurConfigEntry = ConfigEntry[TempurCoordinator]


@dataclass
class Bed:
    """Static information about one Sleeptracker processor and its base."""

    processor_id: int
    device: dict[str, Any]
    hello: dict[str, Any]
    # Side of the base that belongs to the logged-in account (0 or 1).
    side: int | None
    capability: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.device.get("name") or f"Sleeptracker {self.processor_id}"

    @property
    def features(self) -> list[str]:
        return self.hello.get("productFeatures") or []

    @property
    def has_base_controls(self) -> bool:
        return (
            bool(self.device.get("baseSmartCableSupported")) and self.side is not None
        )

    @property
    def has_motors(self) -> bool:
        return self.has_base_controls and FEATURE_MOTORS in self.features

    @property
    def has_environment(self) -> bool:
        return FEATURE_ENV_SENSORS in self.features

    @property
    def anti_snore_supported(self) -> bool:
        return bool(
            (self.device.get("powerBase") or {}).get("antiSnorePresetSupported")
        )

    @property
    def motor_roster(self) -> dict[str, bool]:
        return self.capability.get("motorRoster") or {}

    @property
    def massage_roster(self) -> dict[str, bool]:
        return self.capability.get("massageRoster") or {}

    def ticks_per_degree(self, motor: str) -> float | None:
        power_base = self.device.get("powerBase") or {}
        value = power_base.get(f"{motor}AngleTicksPerDegree")
        return float(value) if value else None


@dataclass
class BedState:
    """Polled state of one bed."""

    snapshot: dict[str, Any] | None = None
    environment: dict[str, float] = field(default_factory=dict)


@dataclass
class TempurData:
    """Everything the coordinator polls."""

    beds: dict[int, BedState] = field(default_factory=dict)
    snore_relief: dict[str, bool] | None = None


class TempurCoordinator(DataUpdateCoordinator[TempurData]):
    """Polls the Sleeptracker cloud and sends commands."""

    config_entry: TempurConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: TempurConfigEntry, api: SleeptrackerApi
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.api = api
        self.beds: dict[int, Bed] = {}

    async def _async_setup(self) -> None:
        """Discover the beds on the account once."""
        try:
            devices = await self.api.get_devices()
            for device in devices:
                processor_id = device["sleeptrackerProcessorID"]
                hello = await self.api.get_hello(processor_id)
                sensors = await self.api.get_sensor_map(processor_id)
                self.beds[processor_id] = _build_bed(
                    processor_id, device, hello, sensors
                )
        except SleeptrackerAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SleeptrackerError as err:
            raise UpdateFailed(f"Could not load beds: {err}") from err
        if not self.beds:
            _LOGGER.warning("No active Sleeptracker device found on this account")

    async def _async_update_data(self) -> TempurData:
        data = TempurData()
        try:
            snapshots: list[dict[str, Any]] | None = None
            for processor_id, bed in self.beds.items():
                state = BedState()
                if bed.has_base_controls:
                    if snapshots is None:
                        snapshots = await self.api.send_command(Command.STATUS)
                    state.snapshot = next(
                        (s for s in snapshots if s.get("side") == bed.side), None
                    )
                if bed.has_environment:
                    state.environment = await self.api.get_environment(processor_id)
                data.beds[processor_id] = state
            if any(bed.has_base_controls for bed in self.beds.values()):
                data.snore_relief = await self.api.get_snore_relief()
        except SleeptrackerAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SleeptrackerError as err:
            raise UpdateFailed(str(err)) from err
        return data

    async def async_send_command(self, command: Command, **extra: Any) -> None:
        """Send a command to the base and refresh the state."""
        await self.async_send_command_raw(command, **extra)
        await self.async_request_refresh()

    async def async_send_command_raw(
        self, command: Command, **extra: Any
    ) -> list[dict[str, Any]]:
        """Send a command and return the status snapshots, without a refresh."""
        try:
            return await self.api.send_command(command, **extra)
        except SleeptrackerAuthError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(str(err)) from err
        except SleeptrackerError as err:
            raise HomeAssistantError(f"Command failed: {err}") from err

    async def async_set_snore_relief(self, **changes: bool) -> None:
        """Change one or both snore relief settings."""
        current = dict((self.data.snore_relief if self.data else None) or {})
        current.update(changes)
        try:
            await self.api.set_snore_relief(
                tilt=bool(current.get("snoreReliefTilt")),
                vibration=bool(current.get("snoreReliefVibration")),
            )
        except SleeptrackerError as err:
            raise HomeAssistantError(f"Could not change snore relief: {err}") from err
        await self.async_request_refresh()


def _build_bed(
    processor_id: int,
    device: dict[str, Any],
    hello: dict[str, Any],
    sensors: list[dict[str, Any]],
) -> Bed:
    """Work out which side of the base the account controls."""
    capabilities: list[dict[str, Any]] = (hello.get("motorMeta") or {}).get(
        "capabilities"
    ) or []
    own_sensor = next((s for s in sensors if s.get("self")), None)
    capability: dict[str, Any] | None = None
    if len(capabilities) == 1:
        capability = capabilities[0]
    elif own_sensor is not None:
        capability = next(
            (c for c in capabilities if c.get("side") == own_sensor.get("unitNumber")),
            None,
        )
    side = capability.get("side") if capability else None
    return Bed(
        processor_id=processor_id,
        device=device,
        hello=hello,
        side=side,
        capability=capability or {},
    )
