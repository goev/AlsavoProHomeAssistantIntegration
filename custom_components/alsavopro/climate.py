"""Support for Alsavo Pro WiFi-enabled pool heaters."""
import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AlsavoProDataCoordinator
from .const import DOMAIN, POWER_MODE_MAP

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AlsavoProClimate(hass.data[DOMAIN][entry.entry_id])])


class AlsavoProClimate(CoordinatorEntity, ClimateEntity):
    """Climate platform for Alsavo Pro pool heater."""

    def __init__(self, coordinator: AlsavoProDataCoordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._data_handler = self.coordinator.data_handler
        self._name = self._data_handler.name

    @property
    def supported_features(self):
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE

    @property
    def unique_id(self):
        return self._data_handler.unique_id

    @property
    def name(self):
        return self._name

    @property
    def available(self):
        return self._data_handler.is_online

    @property
    def hvac_mode(self):
        operating_mode_map = {
            0: HVACMode.COOL,
            1: HVACMode.HEAT,
            2: HVACMode.AUTO,
        }
        return (
            HVACMode.OFF
            if not self._data_handler.is_power_on
            else operating_mode_map.get(self._data_handler.operating_mode)
        )

    @property
    def preset_mode(self):
        return POWER_MODE_MAP.get(self._data_handler.power_mode)

    @property
    def icon(self):
        hvac_mode_icons = {
            HVACMode.HEAT: "mdi:fire",
            HVACMode.COOL: "mdi:snowflake",
            HVACMode.AUTO: "mdi:refresh-auto",
        }
        return hvac_mode_icons.get(self.hvac_mode, "mdi:hvac-off")

    @property
    def hvac_modes(self):
        return [HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO, HVACMode.OFF]

    @property
    def preset_modes(self):
        return ["Silent", "Smart", "Powerful"]

    async def async_set_hvac_mode(self, hvac_mode):
        _LOGGER.info("Setting HVAC mode to %s", hvac_mode)
        hvac_mode_actions = {
            HVACMode.OFF: self._data_handler.set_power_off,
            HVACMode.COOL: self._data_handler.set_cooling_mode,
            HVACMode.HEAT: self._data_handler.set_heating_mode,
            HVACMode.AUTO: self._data_handler.set_auto_mode,
        }
        action = hvac_mode_actions.get(hvac_mode)
        if action:
            success = await action()
            if success:
                _LOGGER.info("HVAC mode set to %s successfully.", hvac_mode)
                await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode):
        _LOGGER.info("Setting preset mode to %s", preset_mode)
        preset_mode_to_power_mode = {
            "Silent": 0,
            "Smart": 1,
            "Powerful": 2,
        }
        power_mode = preset_mode_to_power_mode.get(preset_mode)
        if power_mode is not None:
            success = await self._data_handler.set_power_mode(power_mode)
            if success:
                _LOGGER.info("Preset mode set to %s successfully.", preset_mode)
                await self.coordinator.async_request_refresh()

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def min_temp(self):
        return self._data_handler.get_temperature_from_status(56)

    @property
    def max_temp(self):
        return self._data_handler.get_temperature_from_status(55)

    @property
    def current_temperature(self):
        return self._data_handler.water_in_temperature

    @property
    def target_temperature(self):
        return self._data_handler.target_temperature

    @property
    def target_temperature_step(self):
        return 1

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None or not self._is_valid_temperature(temperature):
            return

        _LOGGER.info("Setting target temperature to %s°C", temperature)
        success = await self._data_handler.set_target_temperature(temperature)
        if success:
            _LOGGER.info("✅ Target temperature set to %s°C", temperature)
        await self.coordinator.async_request_refresh()

    def _is_valid_temperature(self, temperature):
        """Validate temperature against min and max limits."""
        return self.min_temp <= temperature <= self.max_temp

    async def async_update(self):
        _LOGGER.debug("Updating Alsavo Pro Climate data.")
        self._data_handler = self.coordinator.data_handler
