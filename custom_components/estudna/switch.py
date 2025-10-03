import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .estudna import ThingsBoard

_LOGGER = logging.getLogger(__name__)


class EStudnaSwitch(SwitchEntity):
    def __init__(
        self, hass: HomeAssistant, thingsboard: ThingsBoard, device: dict, relay: str
    ):
        self._thingsboard = thingsboard
        self._device = device
        self._relay = relay
        self._state = False
        self._hass = hass

    async def async_update(self) -> None:
        self._state = await self._hass.async_add_executor_job(
            self._thingsboard.get_relay_state, self.device_id, self._relay
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._hass.async_add_executor_job(
            self._thingsboard.set_relay_state, self.device_id, self._relay, True
        )
        await asyncio.sleep(2)
        self._state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._hass.async_add_executor_job(
            self._thingsboard.set_relay_state, self.device_id, self._relay, False
        )
        await asyncio.sleep(2)
        self._state = False
        self.async_write_ha_state()

    @property
    def device_id(self) -> str:
        # eSTUDNA2 has device["id"] as string, eSTUDNA has device["id"]["id"]
        if isinstance(self._device["id"], dict):
            return self._device["id"]["id"]
        return self._device["id"]

    @property
    def unique_id(self) -> str:
        device_id = (
            self._device["id"]["id"]
            if isinstance(self._device["id"], dict)
            else self._device["id"]
        )
        return f"{device_id}_{self._relay}"

    @property
    def device_info(self) -> DeviceInfo:
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
        return f"{self._device.get('name')} {self._relay}"

    @property
    def is_on(self):
        return self._state


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    entities = []
    tb = hass.data[DOMAIN][config_entry.entry_id]

    # eSTUDNA2 doesn't support switches/relays yet
    if tb.device_type == "estudna2":
        async_add_entities(entities)
        return

    devices = await hass.async_add_executor_job(tb.get_devices)
    for device in devices:
        for relay in ["OUT1", "OUT2"]:
            switch = EStudnaSwitch(hass, tb, device, relay)
            await switch.async_update()
            entities.append(switch)
    async_add_entities(entities)
