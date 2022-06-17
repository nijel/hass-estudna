import logging
from datetime import timedelta
from functools import partial

import homeassistant.helpers.config_validation as cv
import voluptuous
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EStudnaSensor
from .const import DOMAIN

REQUIREMENTS = ["requests", "PyJWT[crypto]"]

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        voluptuous.Required(CONF_USERNAME): cv.string,
        voluptuous.Required(CONF_PASSWORD): cv.string,
    }
)

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    entities = []
    tb = hass.data[DOMAIN][config_entry.unique_id]
    devices = await hass.async_add_executor_job(tb.get_devices)
    for device in devices:
        sensor = EStudnaSensor(hass, tb, device)
        states = await sensor.async_update()
        entities.append(sensor)
    async_add_entities(entities)
