import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_device_id
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
        self._device_id = get_device_id(device)
        self._attr_unique_id = f"{self._device_id}_{relay}"

    @property
    def device_id(self) -> str:
        """Return device ID."""
        return self._device_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
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
        return self.coordinator.data.get(f"{self._device_id}_{self._relay}", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            await self.coordinator.thingsboard.set_relay_state(
                self._device_id, self._relay, True
            )
        except Exception as err:
            _LOGGER.error(
                "Failed to turn on relay %s for device %s: %s",
                self._relay,
                self._device_id,
                err,
            )
            raise
        await asyncio.sleep(RELAY_SETTLE_TIME)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            await self.coordinator.thingsboard.set_relay_state(
                self._device_id, self._relay, False
            )
        except Exception as err:
            _LOGGER.error(
                "Failed to turn off relay %s for device %s: %s",
                self._relay,
                self._device_id,
                err,
            )
            raise
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
