"""Config flow for the Flexit Bodø Supreme integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import CONF_DEVICE_ID, CONF_PIN, DEFAULT_NAME, DEFAULT_PORT, DOMAIN
from .coordinator import FlexitUdpClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_DEVICE_ID): vol.All(str, vol.Length(min=16, max=16)),
        vol.Required(CONF_PIN): vol.All(str, vol.Length(min=4, max=4)),
    }
)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot reach the fan."""


class InvalidPin(HomeAssistantError):
    """Error to indicate the PIN was rejected (or malformed)."""


async def _validate_input(hass, data: dict[str, Any]) -> None:
    """Try one status poll against the fan to confirm host/ID/PIN are correct."""
    if not data[CONF_PIN].isdigit():
        raise InvalidPin

    client = FlexitUdpClient(
        hass,
        host=data[CONF_HOST],
        device_id=data[CONF_DEVICE_ID],
        pin=data[CONF_PIN],
        port=data[CONF_PORT],
    )
    try:
        await client.async_get_status()
    except UpdateFailed as err:
        raise CannotConnect from err


class FlexitBodoSupremeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Flexit Bodø Supreme."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            try:
                await _validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidPin:
                errors[CONF_PIN] = "invalid_pin"
            except Exception:  # noqa: BLE001 - guard the flow against any unexpected failure
                _LOGGER.exception("Unexpected exception validating Flexit fan connection")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
