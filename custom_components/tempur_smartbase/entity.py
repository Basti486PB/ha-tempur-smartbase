"""Base entity for the Tempur Smartbase integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import Bed, BedState, TempurCoordinator


class TempurEntity(CoordinatorEntity[TempurCoordinator]):
    """Entity bound to one bed."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TempurCoordinator, bed: Bed, key: str) -> None:
        super().__init__(coordinator)
        self.bed = bed
        self._attr_translation_key = key
        self._attr_unique_id = f"{bed.processor_id}_{bed.side}_{key}"
        device = bed.device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(bed.processor_id))},
            manufacturer=MANUFACTURER,
            model=device.get("modelID") or bed.hello.get("productModel"),
            name=bed.name,
            serial_number=device.get("processorSerialNumber"),
            sw_version=device.get("processorVersionFirmware"),
        )

    @property
    def bed_state(self) -> BedState | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.beds.get(self.bed.processor_id)
