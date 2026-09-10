"""Sensor platform for Flexit Bodø Supreme."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FlexitConfigEntry
from .entity import FlexitEntity
from .protocol import FanStatus


@dataclass(frozen=True, kw_only=True)
class FlexitSensorEntityDescription(SensorEntityDescription):
    """Adds the accessor function that pulls this sensor's value off FanStatus."""

    value_fn: Callable[[FanStatus], int | float]


SENSOR_DESCRIPTIONS: tuple[FlexitSensorEntityDescription, ...] = (
    FlexitSensorEntityDescription(
        key="temperature",
        name="Temperatur",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda status: status.temperature_c,
    ),
    FlexitSensorEntityDescription(
        key="humidity",
        name="Luftfuktighet",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda status: status.humidity_pct,
    ),
    FlexitSensorEntityDescription(
        key="air_quality",
        name="Luftkvalitet",
        icon="mdi:air-filter",
        state_class=SensorStateClass.MEASUREMENT,
        # The fan reports a raw index, not a documented gas concentration -
        # ppm is used loosely here just to give Home Assistant a unit to
        # graph against; treat the number as relative, not an absolute ppm reading.
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        value_fn=lambda status: status.air_quality,
    ),
    FlexitSensorEntityDescription(
        key="speed",
        name="Hastighet",
        icon="mdi:fan",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda status: status.speed,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: FlexitConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        FlexitSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    )


class FlexitSensor(FlexitEntity, SensorEntity):
    """A single read-only measurement from the fan."""

    entity_description: FlexitSensorEntityDescription

    def __init__(self, coordinator, description: FlexitSensorEntityDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> int | float:
        return self.entity_description.value_fn(self._status)
