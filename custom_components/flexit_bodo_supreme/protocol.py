"""
Reverse-engineered local UDP protocol for the Flexit Bodø Supreme bathroom fan.

The fan is controlled locally (no cloud involved) on UDP port 4000. This was
reverse engineered from real packet captures of the official "Flexit Fans"
app talking to a real Bodø Supreme unit — see the project notes for the raw
capture analysis. Every field and command below has been verified either
against the app's own displayed sensor values, or by round-tripping a
command and observing the fan's state change accordingly.

Packet framing:
    fdfd 02 10 <16-byte ASCII device ID> <1-byte PIN length> <ASCII PIN>
    <payload> <2-byte checksum, little-endian>

Checksum:
    checksum = (sum(all bytes from 'fdfd' through the end of payload) - 506) mod 65536
    Verified against 20+ real captured packets (both directions, many shapes), no
    exceptions found.

This module is intentionally free of any Home Assistant or asyncio imports so it
can be unit tested (and re-used) on its own — see coordinator.py for the async
UDP transport that wraps it.
"""
from __future__ import annotations

from dataclasses import dataclass

CHECKSUM_OFFSET = 506
DEVICE_ID_LENGTH = 16
PIN_LENGTH = 4

# Sent by the official app roughly every second while it's in the foreground.
# It's really a list of the register IDs being requested; we don't need to
# understand the individual IDs to use it, it always gets the same shape of
# reply back.
_STATUS_POLL_PAYLOAD = bytes.fromhex(
    "0106070b21254b6683b9ff03122011100f040e0d"
)


class FlexitProtocolError(Exception):
    """Raised when a packet can't be parsed or fails checksum validation."""


def _checksum(body: bytes) -> bytes:
    return ((sum(body) - CHECKSUM_OFFSET) % 65536).to_bytes(2, "little")


def build_packet(device_id: str, pin: str, payload: bytes) -> bytes:
    """Build a complete, checksummed packet ready to send to the fan."""
    if len(device_id) != DEVICE_ID_LENGTH:
        raise ValueError(f"device_id must be exactly {DEVICE_ID_LENGTH} characters")
    if len(pin) != PIN_LENGTH or not pin.isdigit():
        raise ValueError(f"pin must be exactly {PIN_LENGTH} digits")

    header = (
        bytes.fromhex("fdfd0210")
        + device_id.encode("ascii")
        + bytes([len(pin)])
        + pin.encode("ascii")
    )
    body = header + payload
    return body + _checksum(body)


def verify_checksum(packet: bytes) -> bool:
    if len(packet) < 2:
        return False
    return packet[-2:] == _checksum(packet[:-2])


def parse_packet(packet: bytes) -> tuple[str, str, bytes]:
    """Strip the framing off a received packet.

    Returns (device_id, pin, payload). Raises FlexitProtocolError on anything
    that doesn't look like a valid Flexit packet.
    """
    if len(packet) < 4 or packet[0:2] != b"\xfd\xfd":
        raise FlexitProtocolError("missing 'fdfd' magic bytes")
    if not verify_checksum(packet):
        raise FlexitProtocolError("checksum mismatch")

    idlen = packet[3]
    off = 4 + idlen
    if off >= len(packet):
        raise FlexitProtocolError("truncated packet (device id)")
    device_id = packet[4:off].decode("ascii", errors="replace")

    pinlen = packet[off]
    off += 1
    if off + pinlen > len(packet):
        raise FlexitProtocolError("truncated packet (pin)")
    pin = packet[off : off + pinlen].decode("ascii", errors="replace")
    off += pinlen

    payload = packet[off:-2]
    return device_id, pin, payload


@dataclass
class FanStatus:
    """Decoded live status of the fan."""

    temperature_c: float
    humidity_pct: int
    air_quality: int
    speed: int
    forced_ventilation_active: bool
    mode_24h: bool
    countdown: int


def parse_status(payload: bytes) -> FanStatus | None:
    """Decode the 53-byte status response payload (post-checksum-strip).

    Note: during capture analysis, the reference "55-byte" payload included
    the 2-byte trailing checksum. parse_packet() strips that checksum before
    handing us the payload, so the shape we actually see here is 53 bytes —
    all offsets below are unaffected since they're measured from the start.

    Returns None if this payload isn't the status-response shape (e.g. it's
    an ack for a command instead) so callers can tell the difference between
    "not a status packet" and "a status packet with unexpected content" (the
    latter still raises, via the IndexError on genuinely too-short data).
    """
    if len(payload) != 53 or payload[0] != 0x06:
        return None

    return FanStatus(
        temperature_c=int.from_bytes(payload[14:16], "little") / 10,
        humidity_pct=payload[17],
        speed=int.from_bytes(payload[21:23], "little"),
        air_quality=int.from_bytes(payload[39:41], "little"),
        forced_ventilation_active=bool(payload[2]),
        mode_24h=bool(payload[52]),
        countdown=int.from_bytes(payload[8:11], "little"),
    )


# --- outgoing commands -------------------------------------------------

def status_poll(device_id: str, pin: str) -> bytes:
    return build_packet(device_id, pin, _STATUS_POLL_PAYLOAD)


def set_24h_mode(device_id: str, pin: str, on: bool) -> bytes:
    payload = bytes([0x03, 0xFF, 0x03, 0x0D, 0x01 if on else 0x00])
    return build_packet(device_id, pin, payload)


def set_boost(device_id: str, pin: str, on: bool) -> bytes:
    if on:
        payload = bytes.fromhex("030601fc010b07")
    else:
        payload = bytes.fromhex("0301010600fc010b07")
    return build_packet(device_id, pin, payload)
