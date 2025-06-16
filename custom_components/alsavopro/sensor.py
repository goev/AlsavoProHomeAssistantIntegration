"""Sensor platform for Alsavo Pro WiFi-enabled pool heaters."""
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfElectricCurrent,
    UnitOfFrequency,
    EntityCategory,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AlsavoProDataCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            AlsavoProSensor(coordinator, SensorDeviceClass.TEMPERATURE, "Water In", UnitOfTemperature.CELSIUS, 16, False, "mdi:thermometer"),
            AlsavoProSensor(coordinator, SensorDeviceClass.TEMPERATURE, "Water Out", UnitOfTemperature.CELSIUS, 17, False, "mdi:thermometer"),
            AlsavoProSensor(coordinator, SensorDeviceClass.TEMPERATURE, "Ambient", UnitOfTemperature.CELSIUS, 18, False, "mdi:thermometer"),
            AlsavoProSensor(coordinator, SensorDeviceClass.TEMPERATURE, "Cold pipe", UnitOfTemperature.CELSIUS, 19, False, "mdi:thermometer"),
            AlsavoProSensor(coordinator, SensorDeviceClass.TEMPERATURE, "Heating pipe", UnitOfTemperature.CELSIUS, 20, False, "mdi:thermometer"),
            AlsavoProSensor(coordinator, SensorDeviceClass.TEMPERATURE, "IPM module", UnitOfTemperature.CELSIUS, 21, False, "mdi:thermometer"),
            AlsavoProSensor(coordinator, SensorDeviceClass.TEMPERATURE, "Exhaust temperature", UnitOfTemperature.CELSIUS, 23, False, "mdi:thermometer"),
            AlsavoProSensor(coordinator, SensorDeviceClass.TEMPERATURE, "Heating mode target", UnitOfTemperature.CELSIUS, 1, True, "mdi:thermometer"),
            AlsavoProSensor(coordinator, SensorDeviceClass.TEMPERATURE, "Cooling mode target", UnitOfTemperature.CELSIUS, 2, True, "mdi:thermometer"),
            AlsavoProSensor(coordinator, SensorDeviceClass.TEMPERATURE, "Auto mode target", UnitOfTemperature.CELSIUS, 3, True, "mdi:thermometer"),
            AlsavoProSensor(coordinator, None, "Fan speed", "RPM", 22, False, "mdi:fan"),
            AlsavoProSensor(coordinator, SensorDeviceClass.CURRENT, "Compressor", UnitOfElectricCurrent.AMPERE, 26, False, "mdi:current-ac"),
            AlsavoProSensor(coordinator, SensorDeviceClass.FREQUENCY, "Compressor running frequency", UnitOfFrequency.HERTZ, 27, False, "mdi:air-conditioner"),
            AlsavoProSensor(coordinator, None, "Frequency limit code", "", 34, False, "mdi:bell-alert"),
            AlsavoProSensor(coordinator, None, "Alarm code 1", "", 48, False, "mdi:bell-alert"),
            AlsavoProSensor(coordinator, None, "Alarm code 2", "", 49, False, "mdi:bell-alert"),
            AlsavoProSensor(coordinator, None, "Alarm code 3", "", 50, False, "mdi:bell-alert"),
            AlsavoProSensor(coordinator, None, "Alarm code 4", "", 51, False, "mdi:bell-alert"),
            AlsavoProSensor(coordinator, None, "System status code", "", 52, False, "mdi:state-machine"),
            AlsavoProSensor(coordinator, None, "System running code", "", 53, False, "mdi:state-machine"),
            AlsavoProSensor(coordinator, None, "Device type", "", 64, False, "mdi:heat-pump"),
            AlsavoProSensor(coordinator, None, "Main board HW revision", "", 65, False, "mdi:heat-pump"),
            AlsavoProSensor(coordinator, None, "Main board SW revision", "", 66, False, "mdi:heat-pump"),
            AlsavoProSensor(coordinator, None, "Manual HW code", "", 67, False, "mdi:heat-pump"),
            AlsavoProSensor(coordinator, None, "Manual SW code", "", 68, False, "mdi:heat-pump"),
            AlsavoProSensor(coordinator, None, "Power mode", "", 16, True, "mdi:heat-pump"),
            AlsavoProErrorSensor(coordinator, "Error messages"),
        ]
    )


class AlsavoProSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: AlsavoProDataCoordinator,
                 device_class: SensorDeviceClass,
                 name: str,
                 unit: str,
                 idx: int,
                 from_config: bool,
                 icon: str):
        super().__init__(coordinator)
        self.data_coordinator = coordinator
        self._data_handler = self.data_coordinator.data_handler
        self._attr_name = f"{DOMAIN} {self._data_handler.name} {name}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._dataIdx = idx
        self._config = from_config
        self._icon = icon
        self._name = name

        # Optional: assign entity category for config/status sensors
        if self._config:
            self._attr_entity_category = EntityCategory.CONFIG
        elif "Alarm" in name or "code" in name or "revision" in name:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        return self._data_handler.is_online

    @property
    def unique_id(self):
        return f"{self._data_handler.unique_id}_{self._name}"

    @property
    def native_value(self):
        try:
            if self._attr_device_class == SensorDeviceClass.TEMPERATURE:
                return (
                    self._data_handler.get_temperature_from_config(self._dataIdx)
                    if self._config else
                    self._data_handler.get_temperature_from_status(self._dataIdx)
                )
            return (
                self._data_handler.get_config_value(self._dataIdx)
                if self._config else
                self._data_handler.get_status_value(self._dataIdx)
            )
        except Exception as e:
            _LOGGER.warning("Error getting native_value for %s: %s", self._name, e)
            return None

    @property
    def icon(self):
        return self._icon

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._data_handler.unique_id)},
            "name": self._data_handler.name,
            "manufacturer": "Alsavo",
            "model": "Pro Heat Pump",
        }


class AlsavoProErrorSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: AlsavoProDataCoordinator, name: str):
        super().__init__(coordinator)
        self.data_coordinator = coordinator
        self._data_handler = self.data_coordinator.data_handler
        self._attr_name = f"{DOMAIN} {self._data_handler.name} {name}"
        self._name = name
        self._icon = "mdi:alert"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self):
        return f"{self._data_handler.unique_id}_{self._name}"

    @property
    def native_value(self):
        return self._data_handler.errors

    @property
    def icon(self):
        return self._icon

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._data_handler.unique_id)},
            "name": self._data_handler.name,
            "manufacturer": "Alsavo",
            "model": "Pro Heat Pump",
        }
