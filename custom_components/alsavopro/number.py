from homeassistant.components.number import (
    NumberEntity,
    NumberDeviceClass,
    NumberMode
)
from homeassistant.const import EntityCategory

from . import AlsavoProDataCoordinator, AlsavoProEntity
from .const import (
    DOMAIN
)

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)


async def async_setup_entry(hass, entry, async_add_devices):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            AlsavoProNumber(coordinator,
                            "Water temperature calibration",
                            "°C",
                            11,
                            -9.0,
                            9.0,
                            0.1,
                            "mdi:thermometer-lines"),
        ]
    )


class AlsavoProNumber(AlsavoProEntity, CoordinatorEntity, NumberEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: AlsavoProDataCoordinator,
                 name: str,
                 unit: str,
                 idx: int,
                 min_value: float,
                 max_value: float,
                 step: float,
                 icon: str):
        super().__init__(coordinator)
        self.data_coordinator = coordinator
        self._data_handler = self.data_coordinator.data_handler
        self._name = name
        self._attr_native_unit_of_measurement = unit
        self._dataIdx = idx
        self._icon = icon
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_mode = NumberMode.BOX
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def name(self):
        """Return the name of the number entity."""
        return self._name

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        return self._data_handler.is_online

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._data_handler.unique_id}_{self._name}"

    @property
    def native_value(self):
        """Return the current value from config register."""
        return self._data_handler.get_temperature_from_config(self._dataIdx)

    @property
    def icon(self):
        return self._icon

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self._data_handler.set_config(self._dataIdx, int(value * 10))
        await self.coordinator.async_request_refresh()
