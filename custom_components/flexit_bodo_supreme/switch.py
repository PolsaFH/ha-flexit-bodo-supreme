"""Switch platform for Flexit Bodø Supreme (boost and 24-hour mode)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FlexitConfigEntry
from .coordinator import FlexitDataUpdateCoordinator
from .entity import FlexitEntity
from .protocol import FanStatus


@dataclass(frozen=True, kw_only=True)
class FlexitSwitchEntityDescription(SwitchEntityDescription):
    is_on_fn: Callable[[FanStatus], bool]
    set_fn: Callable[[FlexitDataUpdateCoordinator, bool], Any]


SWITCH_DESCRIPTIONS: tuple[FlexitSwitchEntityDescription, ...] = (
    FlexitSwitchEntityDescription(
        key="boost",
        name="Boost",
        icon="mdi:fan-plus",
        is_on_fn=lambda status: status.forced_ventilation_active,
        set_fn=lambda coordinator, on: coordinator.async_set_boost(on),
    ),
    FlexitSwitchEntityDescription(
        key="mode_24h",
        name="24-timers modus",
        icon="mdi:clock-outline",
        is_on_fn=lambda status: status.mode_24h,
        set_fn=lambda coordinator, on: coordinator.async_set_24h_mode(on),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: FlexitConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        FlexitSwitch(coordinator, description) for description in SWITCH_DESCRIPTIONS
    )


class FlexitSwitch(FlexitEntity, SwitchEntity):
    """A single writable mode on the fan (boost or 24-hour mode)."""

    entity_description: FlexitSwitchEntityDescription

    def __init__(self, coordinator, description: FlexitSwitchEntityDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.is_on_fn(self._status)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.entity_description.set_fn(self.coordinator, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.entity_description.set_fn(self.coordinator, False)
