"""Support for Alsavo Pro wifi-enabled pool heaters."""
import logging

from homeassistant.components.climate import (
    PLATFORM_SCHEMA,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode
)

from homeassistant.components.climate.const import (
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_PASSWORD,
    CONF_IP_ADDRESS,
    CONF_PORT,
    CONF_NAME,
    PRECISION_TENTHS,
    TEMP_CELSIUS,
)

from .AlsavoPyCtrl import AlsavoPro
from .const import (
    DOMAIN
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AlsavoProClimate(hass.data[DOMAIN][entry.entry_id])])

""" Climate platform for Alsavo Pro pool heater """
class AlsavoProClimate(ClimateEntity):

    def __init__(self, data_handler: AlsavoPro):
        """Initialize the heater."""
        self._name = data_handler._name
        self._data_handler = data_handler

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._data_handler.uniqueId()

    @property
    def name(self):
        """Return the name of the device, if any."""
        return self._name

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        if self._data_handler.isPowerOn() == False:
            return HVACMode.OFF
        elif self._data_handler.getOperatingMode() == 0:
            return HVACMode.COOL
        elif self._data_handler.getOperatingMode() == 1:
            return HVACMode.HEAT
        elif self._data_handler.getOperatingMode() == 2:
            return HVACMode.AUTO
        return None

    @property
    def fan_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        if self._data_handler.getPowerMode() == 0:
            return FAN_LOW
        elif self._data_handler.getPowerMode() == 1:
            return FAN_MEDIUM
        elif self._data_handler.getPowerMode() == 2:
            return FAN_HIGH
        return None

    @property
    def icon(self):
        """Return nice icon for heater."""
        if self.hvac_mode == HVACMode.HEAT:
            return "mdi:fire"
        elif self.hvac_mode == HVACMode.COOL:
            return "mdi:snowflake"
        elif self.hvac_mode == HVACMode.AUTO:
            return "mdi:refresh-auto"
        return "mdi:hvac-off"

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes."""
        return [HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO, HVACMode.OFF]

    @property
    def fan_modes(self):
        """Return the list of available hvac operation modes."""
        return [FAN_LOW, FAN_MEDIUM, FAN_HIGH]

    async def async_set_hvac_mode(self, hvac_mode):
        """Set hvac mode."""
        if hvac_mode == HVACMode.OFF:
            self._data_handler.setPowerOff()
        elif hvac_mode == HVACMode.COOL:
            self._data_handler.setCoolingMode()
        elif hvac_mode == HVACMode.HEAT:
            self._data_handler.setHeatingMode()
        elif hvac_mode == HVACMode.AUTO:
            self._data_handler.setAutoMode()

        # await self._data_handler.update()
        return

    async def async_set_fan_mode(self, fan_mode):
        """Set hvac mode."""
        if fan_mode == FAN_LOW:
            self._data_handler.setPowerMode(0) #Silent
        elif fan_mode == FAN_MEDIUM:
            self._data_handler.setPowerMode(1) #Smart
        elif fan_mode == FAN_HIGH:
            self._data_handler.setPowerMode(2) #Powerfull
        return

    @property
    def temperature_unit(self):
        """Return the unit of measurement which this device uses."""
        return TEMP_CELSIUS

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._data_handler.getTemperatureFromStatus(56)

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._data_handler.getTemperatureFromStatus(55)

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._data_handler.getWaterInTemperature()

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._data_handler.getTargetTemperature()

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return PRECISION_TENTHS

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._data_handler.setTargetTemperature(temperature)
        return

    async def async_update(self):
        """Get the latest data."""
        await self._data_handler.update()