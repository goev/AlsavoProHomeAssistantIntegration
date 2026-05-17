"""Alsavo Pro pool heat pump integration."""
import asyncio
import logging
from datetime import timedelta

from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_IP_ADDRESS,
    CONF_PORT,
    CONF_NAME,
)

from .AlsavoPyCtrl import AlsavoPro
from .const import (
    DOMAIN,
    SERIAL_NO,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "climate"]

# A single update() call performs the full UDP handshake + query. Allow generous
# headroom so a momentarily-slow device doesn't get cancelled mid-handshake.
UPDATE_TIMEOUT = 15
# Consecutive coordinator failures tolerated before entities go unavailable.
OFFLINE_TOLERANCE = 5


async def async_setup_entry(hass, entry):
    """Set up the Alsavo Pro heater."""
    name = entry.data.get(CONF_NAME)
    serial_no = entry.data.get(SERIAL_NO)
    ip_address = entry.data.get(CONF_IP_ADDRESS)
    port_no = entry.data.get(CONF_PORT)
    password = entry.data.get(CONF_PASSWORD)

    data_handler = AlsavoPro(name, serial_no, ip_address, port_no, password)
    try:
        await data_handler.update()
    except Exception as err:
        raise ConfigEntryNotReady(f"Cannot connect to AlsavoPro pump: {err}") from err
    data_coordinator = AlsavoProDataCoordinator(hass, data_handler)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = data_coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator is not None:
            coordinator.shutdown()
    return unloaded


class AlsavoProDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, data_handler):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="AlsavoPro",
            update_interval=timedelta(seconds=60),
        )
        self.data_handler = data_handler
        self._consecutive_failures = 0
        self._followup_cancel = None

    def schedule_followup_refresh(self):
        """Schedule a single refresh 5 s after a command to read settled state."""
        if self._followup_cancel is not None:
            self._followup_cancel.cancel()
            self._followup_cancel = None

        def _fire():
            self._followup_cancel = None
            self.hass.async_create_task(self.async_request_refresh())

        self._followup_cancel = self.hass.loop.call_later(5, _fire)

    def shutdown(self):
        """Cancel any pending follow-up timer; called on config-entry unload."""
        if self._followup_cancel is not None:
            self._followup_cancel.cancel()
            self._followup_cancel = None

    async def _async_update_data(self):
        _LOGGER.debug("_async_update_data")
        try:
            async with asyncio.timeout(UPDATE_TIMEOUT):
                await self.data_handler.update()
            self._consecutive_failures = 0
            return self.data_handler
        except Exception as err:
            self._consecutive_failures += 1
            if self._consecutive_failures < OFFLINE_TOLERANCE:
                _LOGGER.debug(
                    "Alsavo Pro unreachable (attempt %d/%d): %s",
                    self._consecutive_failures,
                    OFFLINE_TOLERANCE,
                    err,
                )
                return self.data_handler
            raise UpdateFailed(
                f"Alsavo Pro unreachable after {OFFLINE_TOLERANCE} attempts: {err}"
            ) from err
