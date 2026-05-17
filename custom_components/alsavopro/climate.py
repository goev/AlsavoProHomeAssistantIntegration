import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from . import AlsavoProDataCoordinator
from .const import (
    DOMAIN,
    POWER_MODE_MAP,
    DEV_TYPE_FREQALL,
    DEV_TYPE_SINGLE,
    DEV_TYPE_FIXCH,
    DEV_TYPE_FREQCH,
    DEV_TYPE_FIXALL,
    TEMP_COLD_MIN,
    TEMP_COLD_MAX,
    TEMP_HOT_MIN,
    TEMP_HOT_FREQ_MAX,
    TEMP_HOT_FIX_MAX,
)

_LOGGER = logging.getLogger(__name__)

# Inverse of POWER_MODE_MAP — translates HA preset name → register value.
_PRESET_TO_POWER_MODE = {name: code for code, name in POWER_MODE_MAP.items()}

# HVAC modes supported per device type (excluding OFF, which is always available).
# Derived from the official Android app's onClickMod() handler.
_HVAC_MODES_BY_DEV_TYPE = {
    DEV_TYPE_FREQALL: [HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO],
    DEV_TYPE_SINGLE:  [HVACMode.HEAT],
    DEV_TYPE_FIXCH:   [HVACMode.COOL, HVACMode.HEAT],
    DEV_TYPE_FREQCH:  [HVACMode.COOL, HVACMode.HEAT],
    DEV_TYPE_FIXALL:  [HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO],
}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AlsavoProClimate(hass.data[DOMAIN][entry.entry_id])])


class AlsavoProClimate(CoordinatorEntity, ClimateEntity):
    """ Climate platform for Alsavo Pro pool heater """

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1.0
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: AlsavoProDataCoordinator):
        """Initialize the heater."""
        super().__init__(coordinator)
        self._data_handler = coordinator.data_handler
        self._name = self._data_handler.name

    @property
    def unique_id(self):
        return self._data_handler.unique_id

    @property
    def name(self):
        return self._name

    @property
    def available(self) -> bool:
        return self._data_handler.is_online

    @property
    def hvac_mode(self):
        if not self._data_handler.is_power_on:
            return HVACMode.OFF
        operating_mode_map = {
            0: HVACMode.COOL,
            1: HVACMode.HEAT,
            2: HVACMode.AUTO,
        }
        return operating_mode_map.get(self._data_handler.operating_mode, HVACMode.OFF)

    @property
    def hvac_modes(self):
        modes = _HVAC_MODES_BY_DEV_TYPE.get(
            self._data_handler.dev_type,
            [HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO],
        )
        return [HVACMode.OFF, *modes]

    @property
    def preset_mode(self):
        return POWER_MODE_MAP.get(self._data_handler.power_mode)

    @property
    def preset_modes(self):
        # Preset modes only apply to variable-frequency devices.
        if not self._data_handler.is_freq_type:
            return []
        return list(POWER_MODE_MAP.values())

    @property
    def icon(self):
        hvac_mode_icons = {
            HVACMode.HEAT: "mdi:fire",
            HVACMode.COOL: "mdi:snowflake",
            HVACMode.AUTO: "mdi:autorenew",
        }
        return hvac_mode_icons.get(self.hvac_mode, "mdi:hvac-off")

    async def async_turn_on(self):
        await self._data_handler.set_power_on()
        await self.coordinator.async_request_refresh()
        self.coordinator.schedule_followup_refresh()

    async def async_turn_off(self):
        await self._data_handler.set_power_off()
        await self.coordinator.async_request_refresh()
        self.coordinator.schedule_followup_refresh()

    async def async_set_hvac_mode(self, hvac_mode):
        hvac_mode_actions = {
            HVACMode.OFF: self._data_handler.set_power_off,
            HVACMode.COOL: self._data_handler.set_cooling_mode,
            HVACMode.HEAT: self._data_handler.set_heating_mode,
            HVACMode.AUTO: self._data_handler.set_auto_mode,
        }
        action = hvac_mode_actions.get(hvac_mode)
        if action is None:
            return
        await action()
        await self.coordinator.async_request_refresh()
        self.coordinator.schedule_followup_refresh()

    async def async_set_preset_mode(self, preset_mode):
        power_mode = _PRESET_TO_POWER_MODE.get(preset_mode)
        if power_mode is None:
            return
        await self._data_handler.set_power_mode(power_mode)
        await self.coordinator.async_request_refresh()
        self.coordinator.schedule_followup_refresh()

    @property
    def min_temp(self):
        if self.hvac_mode == HVACMode.HEAT:
            return TEMP_HOT_MIN
        return TEMP_COLD_MIN

    @property
    def max_temp(self):
        if self.hvac_mode == HVACMode.COOL:
            return TEMP_COLD_MAX
        # Heat and Auto share the same upper bound; it varies by device type.
        return TEMP_HOT_FREQ_MAX if self._data_handler.is_freq_type else TEMP_HOT_FIX_MAX

    @property
    def current_temperature(self):
        return self._data_handler.water_in_temperature

    @property
    def target_temperature(self):
        return self._data_handler.target_temperature

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self._data_handler.set_target_temperature(temperature)
        await self.coordinator.async_request_refresh()
        self.coordinator.schedule_followup_refresh()
