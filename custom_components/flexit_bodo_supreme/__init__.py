"""The Flexit Bodø Supreme integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_ID, CONF_PIN
from .coordinator import FlexitDataUpdateCoordinator, FlexitUdpClient

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


@dataclass
class FlexitRuntimeData:
    coordinator: FlexitDataUpdateCoordinator


FlexitConfigEntry = ConfigEntry[FlexitRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: FlexitConfigEntry) -> bool:
    """Set up Flexit Bodø Supreme from a config entry."""
    client = FlexitUdpClient(
        hass,
        host=entry.data[CONF_HOST],
        device_id=entry.data[CONF_DEVICE_ID],
        pin=entry.data[CONF_PIN],
        port=entry.data[CONF_PORT],
    )
    coordinator = FlexitDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = FlexitRuntimeData(coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FlexitConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
