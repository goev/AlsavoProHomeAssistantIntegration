"""Number entities for Alsavo Pro installer-level settings."""
from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AlsavoProDataCoordinator
from .AlsavoPyCtrl import AlsavoPro
from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class AlsavoNumberSpec:
    key: str
    name: str
    icon: str
    min_value: float
    max_value: float
    step: float
    unit: str
    device_class: NumberDeviceClass | None
    getter: Callable[[AlsavoPro], float]
    setter: Callable[[AlsavoPro, float], Awaitable[None]]


# Bounds match the official Android app (HtcHpParamActivity / TbParamItem).
NUMBER_SPECS: tuple[AlsavoNumberSpec, ...] = (
    AlsavoNumberSpec(
        key="defrost_in_temp",
        name="Defrost in temperature",
        icon="mdi:snowflake-melt",
        min_value=-30,
        max_value=0,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        getter=lambda dh: dh.defrost_in_temp,
        setter=lambda dh, v: dh.set_defrost_in_temp(v),
    ),
    AlsavoNumberSpec(
        key="defrost_out_temp",
        name="Defrost out temperature",
        icon="mdi:snowflake-off",
        min_value=2,
        max_value=30,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        getter=lambda dh: dh.defrost_out_temp,
        setter=lambda dh, v: dh.set_defrost_out_temp(v),
    ),
    AlsavoNumberSpec(
        key="defrost_in_time",
        name="Defrost in time",
        icon="mdi:timer-sand",
        min_value=30,
        max_value=90,
        step=1,
        unit=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        getter=lambda dh: dh.defrost_in_time,
        setter=lambda dh, v: dh.set_defrost_in_time(int(v)),
    ),
    AlsavoNumberSpec(
        key="defrost_out_time",
        name="Defrost out time",
        icon="mdi:timer-sand-complete",
        min_value=1,
        max_value=12,
        step=1,
        unit=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        getter=lambda dh: dh.defrost_out_time,
        setter=lambda dh, v: dh.set_defrost_out_time(int(v)),
    ),
    AlsavoNumberSpec(
        key="water_compensation",
        name="Water temperature compensation",
        icon="mdi:thermometer-plus",
        min_value=-9.0,
        max_value=9.0,
        step=0.1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        getter=lambda dh: dh.water_compensation,
        setter=lambda dh, v: dh.set_water_compensation(v),
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AlsavoProDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AlsavoProNumber(coordinator, spec) for spec in NUMBER_SPECS)


class AlsavoProNumber(CoordinatorEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: AlsavoProDataCoordinator, spec: AlsavoNumberSpec):
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._data_handler: AlsavoPro = coordinator.data_handler
        self._spec = spec
        self._attr_icon = spec.icon
        self._attr_native_min_value = spec.min_value
        self._attr_native_max_value = spec.max_value
        self._attr_native_step = spec.step
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = spec.device_class

    @property
    def name(self) -> str:
        return f"{DOMAIN}_{self._data_handler.name}_{self._spec.name}"

    @property
    def unique_id(self) -> str:
        return f"{self._data_handler.unique_id}_{self._spec.key}"

    @property
    def available(self) -> bool:
        return self._data_handler.is_online

    @property
    def native_value(self) -> float:
        return self._spec.getter(self._data_handler)

    async def async_set_native_value(self, value: float) -> None:
        await self._spec.setter(self._data_handler, value)
        self._coordinator.schedule_followup_refresh()
