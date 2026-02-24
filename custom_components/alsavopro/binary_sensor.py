from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory

from . import AlsavoProDataCoordinator, AlsavoProEntity
from .const import DOMAIN

from homeassistant.helpers.update_coordinator import CoordinatorEntity


async def async_setup_entry(hass, entry, async_add_devices):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices([
        AlsavoProConnectivitySensor(coordinator),
        AlsavoProFrostProtectionSensor(coordinator),
    ])


class AlsavoProConnectivitySensor(AlsavoProEntity, CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: AlsavoProDataCoordinator):
        super().__init__(coordinator)
        self.data_coordinator = coordinator
        self._data_handler = self.data_coordinator.data_handler

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Connectivity"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._data_handler.unique_id}_connectivity"

    @property
    def is_on(self) -> bool:
        """Return True if the heat pump is connected."""
        return self._data_handler.is_online


class AlsavoProFrostProtectionSensor(AlsavoProEntity, CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.COLD

    def __init__(self, coordinator: AlsavoProDataCoordinator):
        super().__init__(coordinator)
        self.data_coordinator = coordinator
        self._data_handler = self.data_coordinator.data_handler

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Frost protection"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._data_handler.unique_id}_frost_protection"

    @property
    def is_on(self) -> bool:
        """Return True if frost protection is active (AlarmCode2 bit 64)."""
        return self._data_handler.is_frost_protection
