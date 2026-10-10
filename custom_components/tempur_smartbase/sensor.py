"""Sensors for the Tempur Smartbase."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    DEGREE,
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MASSAGE_PATTERNS
from .coordinator import Bed, BedState, TempurConfigEntry, TempurCoordinator
from .entity import TempurEntity


@dataclass(frozen=True, kw_only=True)
class TempurSensorDescription(SensorEntityDescription):
    """Describes a value read from the polled bed state."""

    value: Callable[[Bed, BedState], Any]
    supported: Callable[[Bed], bool]


def _snapshot(state: BedState, *path: str) -> Any:
    value: Any = state.snapshot
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _angle(motor: str) -> Callable[[Bed, BedState], float | None]:
    def value(bed: Bed, state: BedState) -> float | None:
        pulses = _snapshot(state, motor, "motor", "pulseCount")
        ticks = bed.ticks_per_degree(motor)
        if pulses is None or not ticks:
            return None
        return round(pulses / ticks, 1)

    return value


def _massage_timer(bed: Bed, state: BedState) -> float | None:
    minutes = _snapshot(state, "massageTimerMins")
    seconds = _snapshot(state, "massageTimerSecs")
    if minutes is None and seconds is None:
        return None
    return round((minutes or 0) + (seconds or 0) / 60, 1)


def _has_massage(bed: Bed) -> bool:
    return bed.has_base_controls and any(
        bed.massage_roster.get(z) for z in ("head", "foot")
    )


SENSORS: tuple[TempurSensorDescription, ...] = (
    TempurSensorDescription(
        key="head_angle",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        value=_angle("head"),
        supported=lambda bed: (
            bed.has_base_controls and bool(bed.ticks_per_degree("head"))
        ),
    ),
    TempurSensorDescription(
        key="foot_angle",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        value=_angle("foot"),
        supported=lambda bed: (
            bed.has_base_controls and bool(bed.ticks_per_degree("foot"))
        ),
    ),
    TempurSensorDescription(
        key="head_massage_strength",
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda bed, s: _snapshot(s, "head", "massage", "strength"),
        supported=lambda bed: (
            bed.has_base_controls and bool(bed.massage_roster.get("head"))
        ),
    ),
    TempurSensorDescription(
        key="foot_massage_strength",
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda bed, s: _snapshot(s, "foot", "massage", "strength"),
        supported=lambda bed: (
            bed.has_base_controls and bool(bed.massage_roster.get("foot"))
        ),
    ),
    TempurSensorDescription(
        key="massage_pattern",
        device_class=SensorDeviceClass.ENUM,
        options=list(MASSAGE_PATTERNS.values()),
        value=lambda bed, s: MASSAGE_PATTERNS.get(_snapshot(s, "massagePattern")),
        supported=_has_massage,
    ),
    TempurSensorDescription(
        key="massage_timer",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value=_massage_timer,
        supported=_has_massage,
    ),
    TempurSensorDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda bed, s: s.environment.get("degreesCelsius"),
        supported=lambda bed: bed.has_environment,
    ),
    TempurSensorDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda bed, s: s.environment.get("humidityPercentage"),
        supported=lambda bed: bed.has_environment,
    ),
    TempurSensorDescription(
        key="co2",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda bed, s: s.environment.get("co2Ppm"),
        supported=lambda bed: bed.has_environment,
    ),
    TempurSensorDescription(
        key="voc",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_BILLION,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda bed, s: s.environment.get("vocPpb"),
        supported=lambda bed: bed.has_environment,
    ),
    TempurSensorDescription(
        key="wifi_signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement="dBm",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value=lambda bed, s: bed.device.get("lastWiFiRSSI"),
        supported=lambda bed: bed.device.get("lastWiFiRSSI") is not None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TempurConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        TempurSensor(coordinator, bed, description)
        for bed in coordinator.beds.values()
        for description in SENSORS
        if description.supported(bed)
    )


class TempurSensor(TempurEntity, SensorEntity):
    """A value from the polled bed state."""

    entity_description: TempurSensorDescription

    def __init__(
        self,
        coordinator: TempurCoordinator,
        bed: Bed,
        description: TempurSensorDescription,
    ) -> None:
        super().__init__(coordinator, bed, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        state = self.bed_state
        if state is None:
            return None
        return self.entity_description.value(self.bed, state)
