"""Async UDP transport + DataUpdateCoordinator for the Flexit Bodø Supreme."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, UDP_RETRIES, UDP_TIMEOUT
from . import protocol
from .protocol import FanStatus

_LOGGER = logging.getLogger(__name__)


class _SingleResponseProtocol(asyncio.DatagramProtocol):
    """Minimal asyncio UDP protocol that resolves a future with the first datagram received."""

    def __init__(self) -> None:
        self.transport: asyncio.DatagramTransport | None = None
        self.response: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:  # type: ignore[override]
        self.transport = transport

    def datagram_received(self, data: bytes, addr) -> None:  # type: ignore[override]
        if not self.response.done():
            self.response.set_result(data)

    def error_received(self, exc: Exception) -> None:  # type: ignore[override]
        if not self.response.done():
            self.response.set_exception(exc)


class FlexitUdpClient:
    """Sends a request packet to the fan and waits for the matching reply."""

    def __init__(self, hass: HomeAssistant, host: str, device_id: str, pin: str, port: int = DEFAULT_PORT) -> None:
        self._hass = hass
        self.host = host
        self.port = port
        self.device_id = device_id
        self.pin = pin

    async def _send_and_wait(self, packet: bytes) -> bytes:
        loop = asyncio.get_running_loop()
        transport, proto = await loop.create_datagram_endpoint(
            _SingleResponseProtocol,
            remote_addr=(self.host, self.port),
        )
        try:
            transport.sendto(packet)
            return await asyncio.wait_for(proto.response, timeout=UDP_TIMEOUT)
        finally:
            transport.close()

    async def _request(self, packet: bytes) -> bytes:
        last_error: Exception | None = None
        for attempt in range(UDP_RETRIES + 1):
            try:
                raw = await self._send_and_wait(packet)
                _device_id, _pin, payload = protocol.parse_packet(raw)
                return payload
            except (asyncio.TimeoutError, OSError, protocol.FlexitProtocolError) as err:
                last_error = err
                _LOGGER.debug(
                    "Flexit request attempt %d/%d failed: %s", attempt + 1, UDP_RETRIES + 1, err
                )
        raise UpdateFailed(f"Could not reach Flexit fan at {self.host}:{self.port}: {last_error}")

    async def async_get_status(self) -> FanStatus:
        packet = protocol.status_poll(self.device_id, self.pin)
        payload = await self._request(packet)
        status = protocol.parse_status(payload)
        if status is None:
            raise UpdateFailed("Unexpected response shape from Flexit fan (not a status packet)")
        return status

    async def async_set_boost(self, on: bool) -> None:
        packet = protocol.set_boost(self.device_id, self.pin, on)
        await self._request(packet)

    async def async_set_24h_mode(self, on: bool) -> None:
        packet = protocol.set_24h_mode(self.device_id, self.pin, on)
        await self._request(packet)


class FlexitDataUpdateCoordinator(DataUpdateCoordinator[FanStatus]):
    """Polls the fan on a fixed interval and hands out the decoded status."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: FlexitUdpClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{entry.title} status",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> FanStatus:
        return await self.client.async_get_status()

    async def async_set_boost(self, on: bool) -> None:
        await self.client.async_set_boost(on)
        await self.async_request_refresh()

    async def async_set_24h_mode(self, on: bool) -> None:
        await self.client.async_set_24h_mode(on)
        await self.async_request_refresh()
