"""eSTUDNA component for Home Assistant."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_DEVICE_TYPE, DEVICE_TYPE_ESTUDNA, DOMAIN
from .estudna import ThingsBoard

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.SWITCH]
SCAN_INTERVAL = timedelta(seconds=60)


def get_device_id(device: dict) -> str:
    """Extract device ID from device dict.

    eSTUDNA2 has device["id"] as string, eSTUDNA has device["id"]["id"].
    """
    if isinstance(device["id"], dict):
        return device["id"]["id"]
    return device["id"]


class EStudnaCoordinator(DataUpdateCoordinator):
    """Class to manage fetching eSTUDNA data."""

    def __init__(
        self, hass: HomeAssistant, thingsboard: ThingsBoard, devices: list[dict]
    ):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.thingsboard = thingsboard
        self.devices = devices

    async def _async_update_data(self):
        """Fetch data from API."""
        data = {}
        for device in self.devices:
            device_id = get_device_id(device)
            # Fetch sensor level
            try:
                level = await self.thingsboard.get_estudna_level(device_id)
                data[f"{device_id}_level"] = level
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Error fetching level for device %s: %s", device_id, err)
                data[f"{device_id}_level"] = None

            # Fetch relay states
            for relay in ["OUT1", "OUT2"]:
                try:
                    state = await self.thingsboard.get_relay_state(device_id, relay)
                    data[f"{device_id}_{relay}"] = state
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug(
                        "Error fetching relay %s state for device %s: %s",
                        relay,
                        device_id,
                        err,
                    )
                    data[f"{device_id}_{relay}"] = False

        return data


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up estudna from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    device_type = entry.data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_ESTUDNA)

    # Get shared aiohttp session
    session = async_get_clientsession(hass)

    # Initialize ThingsBoard with async session
    tb = ThingsBoard(device_type=device_type, session=session)

    # Login using async method
    await tb.login(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

    # Get devices
    devices = await tb.get_devices()

    # Create coordinator
    coordinator = EStudnaCoordinator(hass, tb, devices)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.thingsboard.close()

    return unload_ok
