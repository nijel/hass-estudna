import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_device_id
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EStudnaSensor(CoordinatorEntity, SensorEntity):
    """Representation of an eSTUDNA sensor."""

    def __init__(self, coordinator, device: dict):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = get_device_id(device)
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfLength.METERS
        self._attr_unique_id = self._device_id

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
        """Return the name of the sensor."""
        return self._device.get("name")

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(f"{self._device_id}_level")

    @property
    def available(self):
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get(f"{self._device_id}_level") is not None
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up eSTUDNA sensors from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [EStudnaSensor(coordinator, device) for device in coordinator.devices]

    async_add_entities(entities)
