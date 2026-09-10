"""Constants for the Flexit Bodø Supreme integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "flexit_bodo_supreme"

CONF_DEVICE_ID = "device_id"
CONF_PIN = "pin"

DEFAULT_PORT = 4000
DEFAULT_NAME = "Bad vifte"

# The Homey community found that polling faster than ~30s makes the air
# quality reading drift/misbehave, and recommended ~90s. We default to that.
DEFAULT_SCAN_INTERVAL = timedelta(seconds=90)

UDP_TIMEOUT = 5  # seconds to wait for a single response before giving up
UDP_RETRIES = 2  # extra attempts if a request times out (UDP has no delivery guarantee)

MANUFACTURER = "Flexit"
MODEL = "Bodø Supreme"
