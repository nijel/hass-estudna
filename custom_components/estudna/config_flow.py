"""Config flow for estudna integration."""

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import CONF_DEVICE_TYPE, DEVICE_TYPE_ESTUDNA, DEVICE_TYPE_ESTUDNA2, DOMAIN
from .estudna import ThingsBoard

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_DEVICE_TYPE, default=DEVICE_TYPE_ESTUDNA): SelectSelector(
            SelectSelectorConfig(
                options=[
                    {"value": DEVICE_TYPE_ESTUDNA, "label": "eSTUDNA"},
                    {"value": DEVICE_TYPE_ESTUDNA2, "label": "eSTUDNA2"},
                ],
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]
    device_type = data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_ESTUDNA)

    # Get shared aiohttp session
    session = async_get_clientsession(hass)

    tb = ThingsBoard(device_type=device_type, session=session)
    try:
        await tb.login(username, password)
    except aiohttp.ClientError as error:
        raise CannotConnect from error
    except (RuntimeError, ValueError) as error:
        raise InvalidAuth from error


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for estudna."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title="eSTUDNA", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
