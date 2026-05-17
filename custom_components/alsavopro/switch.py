"""Switch entities for Alsavo Pro boolean flags in config register 4."""
from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AlsavoProDataCoordinator
from .AlsavoPyCtrl import AlsavoPro
from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class AlsavoSwitchSpec:
    key: str
    name: str
    icon: str
    getter: Callable[[AlsavoPro], bool]
    setter: Callable[[AlsavoPro, bool], Awaitable[None]]


SWITCH_SPECS: tuple[AlsavoSwitchSpec, ...] = (
    AlsavoSwitchSpec(
        key="timer_on_enabled",
        name="Timer on enabled",
        icon="mdi:timer-play-outline",
        getter=lambda dh: dh.is_timer_on_enabled,
        setter=lambda dh, v: dh.set_timer_on_enabled(v),
    ),
    AlsavoSwitchSpec(
        key="timer_off_enabled",
        name="Timer off enabled",
        icon="mdi:timer-stop-outline",
        getter=lambda dh: dh.is_timer_off_enabled,
        setter=lambda dh, v: dh.set_timer_off_enabled(v),
    ),
    AlsavoSwitchSpec(
        key="pump_run_mode",
        name="Pump continuous run",
        icon="mdi:pump",
        getter=lambda dh: dh.is_pump_run_mode_enabled,
        setter=lambda dh, v: dh.set_pump_run_mode_enabled(v),
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AlsavoProDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AlsavoProSwitch(coordinator, spec) for spec in SWITCH_SPECS)


class AlsavoProSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator: AlsavoProDataCoordinator, spec: AlsavoSwitchSpec):
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
    def is_on(self) -> bool:
        return self._spec.getter(self._data_handler)

    async def async_turn_on(self, **_kwargs) -> None:
        await self._spec.setter(self._data_handler, True)
        self._coordinator.schedule_followup_refresh()

    async def async_turn_off(self, **_kwargs) -> None:
        await self._spec.setter(self._data_handler, False)
        self._coordinator.schedule_followup_refresh()
