"""Base entity for Flexit Bodø Supreme."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import FlexitDataUpdateCoordinator
from .protocol import FanStatus


class FlexitEntity(CoordinatorEntity[FlexitDataUpdateCoordinator]):
    """Common base: wires up device_info and unique_id prefixing."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FlexitDataUpdateCoordinator, unique_id_suffix: str) -> None:
        super().__init__(coordinator)
        device_id = coordinator.client.device_id
        self._attr_unique_id = f"{device_id}_{unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=coordinator.entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
            # Hints Home Assistant to place the device in the "Bad" (bathroom)
            # area when it's first created, since that's where this fan
            # physically lives. The user can still move it, this is just the
            # sensible default.
            suggested_area="Bad",
        )

    @property
    def _status(self) -> FanStatus:
        return self.coordinator.data
