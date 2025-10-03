"""eSTUDNA component for Home Assistant."""

from functools import partial

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import CONF_DEVICE_TYPE, DEVICE_TYPE_ESTUDNA, DOMAIN
from .estudna import ThingsBoard

PLATFORMS = [Platform.SENSOR, Platform.SWITCH]


class EStudnaSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, thingsboard: ThingsBoard, device: dict):
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
        # eSTUDNA2 has device["id"] as string, eSTUDNA has device["id"]["id"]
        if isinstance(self._device["id"], dict):
            return self._device["id"]["id"]
        return self._device["id"]

    @property
    def device_info(self) -> DeviceInfo:
        # eSTUDNA2 has device["id"] as string, eSTUDNA has device["id"]["id"]
        device_id = (
            self._device["id"]["id"]
            if isinstance(self._device["id"], dict)
            else self._device["id"]
        )
        return DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            model=self._device.get("type"),
            manufacturer="SEA Praha",
            name=self._device.get("name"),
        )

    @property
    def name(self):
        return self._device.get("name")

    @property
    def state(self):
        return self._state

    @property
    def available(self):
        return self._state is not None

    @property
    def unit_of_measurement(self) -> str:
        return UnitOfLength.METERS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up estudna from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    device_type = entry.data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_ESTUDNA)
    tb = ThingsBoard(device_type=device_type)
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
