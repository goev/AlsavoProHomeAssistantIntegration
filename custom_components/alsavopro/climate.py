import logging
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]

class AlsavoClimateEntity(ClimateEntity):
    def __init__(self, coordinator, alsavo):
        self._coordinator = coordinator
        self._alsavo = alsavo
        self._name = "Alsavo Pro"
        self._unique_id = "alsavo_pro_climate"
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_hvac_modes = HVAC_MODES
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_min_temp = 10.0
        self._attr_max_temp = 40.0

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def current_temperature(self):
        return self._coordinator.data.get("current_temp")

    @property
    def target_temperature(self):
        return self._coordinator.data.get("target_temp")

    @property
    def hvac_mode(self):
        mode = self._coordinator.data.get("mode")
        if mode == 0:
            return HVACMode.OFF
        elif mode == 1:
            return HVACMode.HEAT
        elif mode == 2:
            return HVACMode.COOL
        return HVACMode.OFF

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return

        try:
            packet = self._alsavo.build_set_temp_packet(temp)
            self._alsavo.udp.sendto(packet)
            await self._coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Unable to set temperature: {e}")

    async def async_set_hvac_mode(self, hvac_mode):
        mode_code = {
            HVACMode.OFF: 0,
            HVACMode.HEAT: 1,
            HVACMode.COOL: 2,
        }.get(hvac_mode, 0)

        try:
            packet = self._alsavo.build_set_mode_packet(mode_code)
            self._alsavo.udp.sendto(packet)
            await self._coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Unable to set HVAC mode: {e}")

    async def async_update(self):
        await self._coordinator.async_request_refresh()
