"""eSTUDNA component for Home Assistant."""
from functools import partial
from typing import Dict

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (CONF_PASSWORD, CONF_USERNAME, LENGTH_METERS,
                                 Platform)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .estudna import ThingsBoard

PLATFORMS = [Platform.SENSOR]


class EStudnaSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, thingsboard: ThingsBoard, device: Dict):
        self._thingsboard = thingsboard
        self._device = device
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = None
        self._hass = hass

    async def async_update(self) -> None:
        try:
            self._state = await self._hass.async_add_executor_job(
                self._thingsboard.get_estudna_level, self.unique_id
            )
        except IndexError:
            self._state = None

    @property
    def unique_id(self) -> str:
        return self._device["id"]["id"]

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device["id"]["id"])},
            model=self._device["type"],
            manufacturer="SEA Praha",
            name=self._device["name"],
        )

    @property
    def name(self):
        return self._device["name"]

    @property
    def state(self):
        return self._state

    @property
    def available(self):
        return self._state is not None

    @property
    def unit_of_measurement(self) -> str:
        return LENGTH_METERS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up estudna from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    tb = ThingsBoard()
    await hass.loop.run_in_executor(
        None, partial(tb.login, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    )
    hass.data[DOMAIN][entry.entry_id] = tb

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id).close()

    return unload_ok
