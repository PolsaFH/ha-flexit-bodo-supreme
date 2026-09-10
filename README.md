# Flexit Bodø Supreme — Home Assistant Integration

<img src="icon.png" width="96" align="right" alt="Flexit Bodø Supreme integration icon">

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A [Home Assistant](https://www.home-assistant.io/) custom integration for the **Flexit Bodø Supreme** bathroom extractor fan, reverse-engineered from real packet captures of the official "Flexit Fans" app — there is no official or documented API for this device.

It talks directly to the fan over your LAN (local UDP, port 4000) — nothing goes through Flexit's servers.

## Why this exists

The Bodø Supreme has no official Home Assistant integration. This integration was built by capturing and reverse-engineering the local UDP protocol the "Flexit Fans" app uses to talk to the fan — every field and command has been verified either against the app's own displayed sensor values, or by round-tripping a command and observing the fan's state change accordingly.

## Features

- **Sensors**: temperature, humidity, air quality (relative index), fan speed
- **Switches**: Boost (forced ventilation), 24-hour mode
- Device is placed in the "Bad" (bathroom) area by default when first added

## Installation

### HACS (recommended)

1. HACS → the three-dot menu (top right) → **Custom repositories**
2. Add this repository URL, category **Integration**
3. Search for "Flexit Bodø Supreme" in HACS and install it
4. Restart Home Assistant

### Manual

1. Copy `custom_components/flexit_bodo_supreme` into your Home Assistant `custom_components` folder
2. Restart Home Assistant

## Configuration

Settings → Devices & Services → Add Integration → search for **Flexit Bodø Supreme**.

You'll need:
- **Name**: what to call this fan in Home Assistant
- **IP address**: the fan's local IP (easiest if you set a static/reserved IP for it in your router)
- **Port**: default `4000`
- **Device ID**: 16 characters, same as used in the Flexit Fans app
- **PIN**: 4 digits, same as used in the Flexit Fans app

The integration polls the fan for real during setup to verify the device ID/PIN before creating the entry.

## Entities

| Entity | Type | Notes |
|---|---|---|
| `sensor.<name>_temperature` | Sensor | °C |
| `sensor.<name>_humidity` | Sensor | % |
| `sensor.<name>_air_quality` | Sensor | Raw index reported by the fan, not a calibrated ppm reading — treat as relative |
| `sensor.<name>_speed` | Sensor | Current fan speed |
| `switch.<name>_boost` | Switch | Forced ventilation ("boost") mode |
| `switch.<name>_24_timers_modus` | Switch | 24-hour mode |

## Technical background

The fan is controlled locally over UDP on port 4000 — no cloud involved. This was reverse engineered from real packet captures of the official "Flexit Fans" app talking to a real Bodø Supreme unit.

Packet framing:

```
fdfd 02 10 <16-byte ASCII device ID> <1-byte PIN length> <ASCII PIN> <payload> <2-byte checksum, little-endian>
```

Checksum: `(sum(all bytes from 'fdfd' through the end of payload) - 506) mod 65536` — verified against 20+ real captured packets (both directions, many shapes), no exceptions found.

The status response is a fixed 53-byte payload (after the checksum is stripped) starting with `0x06`, decoded into temperature, humidity, air quality, speed, boost state, 24h-mode state, and a countdown value. Commands (boost on/off, 24h mode on/off) are short fixed byte sequences sent the same way, with the fan replying with an ack rather than a fresh status packet.

The integration polls every 90 seconds by default — the Homey community found that polling this fan faster than ~30s makes the air quality reading drift/misbehave, so 90s was picked as a safe default.

None of this is a secret extracted from Flexit's servers — it's all observed from the local network traffic between the official app and the fan on your own LAN. This integration doesn't bypass any authentication; it talks to the fan with the device ID and PIN you provide, the same way the app does.

## Known limitations

- Only the fields exposed by the app's own dashboard have been decoded from the status payload; other bytes in the 53-byte response are unidentified and not yet exposed as entities.
- No cloud/away-from-home support — this is local-network-only, same as the protocol it's built on.

## Disclaimer

Not affiliated with or endorsed by Flexit. Provided as-is; use at your own risk. This integration was built by observing the official app's own local network traffic — no data leaves your LAN except to the fan itself.

## Contributing

Issues and PRs welcome — especially for decoding more of the status payload.

## License

MIT — see [LICENSE](LICENSE).
