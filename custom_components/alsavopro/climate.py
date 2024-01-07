"""Support for Alsavo Pro wifi-enabled pool heaters."""
import logging

from homeassistant.components.climate import (
    PLATFORM_SCHEMA,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_PASSWORD,
    CONF_IP_ADDRESS,
    CONF_PORT,
    CONF_NAME,
    PRECISION_TENTHS,
    UnitOfTemperature,
)

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from . import AlsavoProDataCoordinator
from .const import (
    DOMAIN,
    POWER_MODE_MAP
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AlsavoProClimate(hass.data[DOMAIN][entry.entry_id])])


class AlsavoProClimate(CoordinatorEntity, ClimateEntity):
    """ Climate platform for Alsavo Pro pool heater """

    def __init__(self, coordinator: AlsavoProDataCoordinator):
        """Initialize the heater."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._data_handler = self.coordinator.data_handler
        self._name = self._data_handler.name

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._data_handler.unique_id

    @property
    def name(self):
        """Return the name of the device, if any."""
        return self._name

    @property
    def available(self) -> bool:
        """Return True if roller and hub is available."""
        return self._data_handler.is_online

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
    def preset_mode(self):
        """Return Preset modes silent, smart mode."""
        return POWER_MODE_MAP.get(self._data_handler.power_mode)

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
    def preset_modes(self):
        """Return the list of available hvac operation modes."""
        return ['Silent', 'Smart', 'Powerful']

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
            await action()
            await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode):
        """Set hvac preset mode."""
        preset_mode_to_power_mode = {
            'Silent': 0,     # Silent
            'Smart': 1,  # Smart
            'Powerful': 2     # Powerful
        }

        power_mode = preset_mode_to_power_mode.get(preset_mode)
        if power_mode is not None:
            await self._data_handler.set_power_mode(power_mode)
            await self.coordinator.async_request_refresh()

    @property
    def temperature_unit(self):
        """Return the unit of measurement which this device uses."""
        return UnitOfTemperature.CELSIUS

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
        await self._data_handler.set_target_temperature(temperature)
        await self.coordinator.async_request_refresh()

    async def async_update(self):
        """Get the latest data."""
        self._data_handler = self.coordinator.data_handler
