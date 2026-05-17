"""Time entities for Alsavo Pro timer-on / timer-off scheduling."""
from dataclasses import dataclass
from datetime import time
from typing import Awaitable, Callable

from homeassistant.components.time import TimeEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AlsavoProDataCoordinator
from .AlsavoPyCtrl import AlsavoPro
from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class AlsavoTimeSpec:
    key: str
    name: str
    icon: str
    getter: Callable[[AlsavoPro], tuple[int, int]]
    setter: Callable[[AlsavoPro, int, int], Awaitable[None]]


# Register 33/34 store the time as (hour << 8) | minute.
TIME_SPECS: tuple[AlsavoTimeSpec, ...] = (
    AlsavoTimeSpec(
        key="timer_on_time",
        name="Timer on time",
        icon="mdi:clock-start",
        getter=lambda dh: dh.timer_on_hhmm,
        setter=lambda dh, h, m: dh.set_timer_on_hhmm(h, m),
    ),
    AlsavoTimeSpec(
        key="timer_off_time",
        name="Timer off time",
        icon="mdi:clock-end",
        getter=lambda dh: dh.timer_off_hhmm,
        setter=lambda dh, h, m: dh.set_timer_off_hhmm(h, m),
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AlsavoProDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AlsavoProTime(coordinator, spec) for spec in TIME_SPECS)


class AlsavoProTime(CoordinatorEntity, TimeEntity):
    def __init__(self, coordinator: AlsavoProDataCoordinator, spec: AlsavoTimeSpec):
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._data_handler: AlsavoPro = coordinator.data_handler
        self._spec = spec
        self._attr_icon = spec.icon

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
    def native_value(self) -> time | None:
        hour, minute = self._spec.getter(self._data_handler)
        if hour > 23 or minute > 59:
            return None
        return time(hour=hour, minute=minute)

    async def async_set_value(self, value: time) -> None:
        await self._spec.setter(self._data_handler, value.hour, value.minute)
        self._coordinator.schedule_followup_refresh()
