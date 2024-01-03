"""Support for Alsavo Pro wifi-enabled pool heaters."""
import logging

from homeassistant.components.climate import (
    PLATFORM_SCHEMA,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode
)

from homeassistant.components.climate.const import (
    SUPPORT_PRESET_MODE,    
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
    DOMAIN,
    PRESET_LIST
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AlsavoProClimate(hass.data[DOMAIN][entry.entry_id])])


class AlsavoProClimate(ClimateEntity):
    """ Climate platform for Alsavo Pro pool heater """

    def __init__(self, data_handler: AlsavoPro):
        """Initialize the heater."""
        self._name = data_handler.name
        self._data_handler = data_handler

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._data_handler.unique_id

    @property
    def name(self):
        """Return the name of the device, if any."""
        return self._name

    @property
    def hvac_mode(self):
        """Return hvac operation i.e. heat, cool mode."""
        operating_mode_map = {
            0: HVACMode.COOL,
            1: HVACMode.HEAT,
            2: HVACMode.AUTO
        }

        if not self._data_handler.is_power_on:
            return HVACMode.OFF

        return operating_mode_map.get(self._data_handler.operating_mode)

    @property
    def fan_mode(self):
        """Return hvac operation i.e. heat, cool mode."""
        power_mode_map = {
            0: FAN_LOW,
            1: FAN_MEDIUM,
            2: FAN_HIGH
        }

        return power_mode_map.get(self._data_handler.power_mode)

    @property
    def icon(self):
        """Return nice icon for heater."""
        hvac_mode_icons = {
            HVACMode.HEAT: "mdi:fire",
            HVACMode.COOL: "mdi:snowflake",
            HVACMode.AUTO: "mdi:refresh-auto"
        }

        return hvac_mode_icons.get(self.hvac_mode, "mdi:hvac-off")

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
        hvac_mode_actions = {
            HVACMode.OFF: self._data_handler.set_power_off,
            HVACMode.COOL: self._data_handler.set_cooling_mode,
            HVACMode.HEAT: self._data_handler.set_heating_mode,
            HVACMode.AUTO: self._data_handler.set_auto_mode
        }

        action = hvac_mode_actions.get(hvac_mode)
        if action:
            action()

    async def async_set_fan_mode(self, fan_mode):
        """Set hvac fan mode."""
        fan_mode_to_power_mode = {
            FAN_LOW: 0,     # Silent
            FAN_MEDIUM: 1,  # Smart
            FAN_HIGH: 2     # Powerful
        }

        power_mode = fan_mode_to_power_mode.get(fan_mode)
        if power_mode is not None:
            self._data_handler.set_power_mode(power_mode)

    @property
    def temperature_unit(self):
        """Return the unit of measurement which this device uses."""
        return TEMP_CELSIUS

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._data_handler.get_temperature_from_status(56)

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._data_handler.get_temperature_from_status(55)

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._data_handler.water_in_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._data_handler.target_temperature

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return PRECISION_TENTHS

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._data_handler.set_target_temperature(temperature)
        return

    async def async_update(self):
        """Get the latest data."""
        await self._data_handler.update()
