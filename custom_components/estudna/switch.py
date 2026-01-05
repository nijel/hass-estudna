import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Time to wait for relay to settle after state change
RELAY_SETTLE_TIME = 2


class EStudnaSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of an eSTUDNA switch."""

    def __init__(self, coordinator, device: dict, relay: str):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._device = device
        self._relay = relay

    def _get_device_id(self) -> str:
        """Get device ID from device dict."""
        # eSTUDNA2 has device["id"] as string, eSTUDNA has device["id"]["id"]
        if isinstance(self._device["id"], dict):
            return self._device["id"]["id"]
        return self._device["id"]

    @property
    def device_id(self) -> str:
        """Return device ID."""
        return self._get_device_id()

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._get_device_id()}_{self._relay}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        device_id = self.device_id
        return DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            model=self._device.get("type"),
            manufacturer="SEA Praha",
            name=self._device.get("name"),
        )

    @property
    def name(self):
        """Return the name of the switch."""
        return f"{self._device.get('name')} {self._relay}"

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self.coordinator.data.get(f"{self.device_id}_{self._relay}", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.thingsboard.set_relay_state(
            self.device_id, self._relay, True
        )
        await asyncio.sleep(RELAY_SETTLE_TIME)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.thingsboard.set_relay_state(
            self.device_id, self._relay, False
        )
        await asyncio.sleep(RELAY_SETTLE_TIME)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up eSTUDNA switches from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        EStudnaSwitch(coordinator, device, relay)
        for device in coordinator.devices
        for relay in ["OUT1", "OUT2"]
    ]

    async_add_entities(entities)
