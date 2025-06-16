"""Alsavo Pro pool heat pump integration."""

import logging
from datetime import timedelta
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
from .const import DOMAIN, SERIAL_NO

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "sensor"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Legacy setup (not used with config entries)."""
    _LOGGER.debug("async_setup called for Alsavo Pro integration.")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alsavo Pro from a config entry."""
    _LOGGER.info("Setting up Alsavo Pro heater: %s", entry.data.get(CONF_NAME))

    try:
        name = entry.data[CONF_NAME]
        serial_no = entry.data[SERIAL_NO]
        ip_address = entry.data[CONF_IP_ADDRESS]
        port_no = entry.data[CONF_PORT]
        password = entry.data[CONF_PASSWORD]

        # Initialize and fetch initial data
        device = AlsavoPro(name, serial_no, ip_address, port_no, password)
        await device.update()

        coordinator = AlsavoProDataCoordinator(hass, device)
        await coordinator.async_config_entry_first_refresh()

        # Store coordinator
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

        # Setup platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        _LOGGER.info("Alsavo Pro setup complete for %s", name)
        return True

    except Exception as ex:
        _LOGGER.exception("Error setting up Alsavo Pro heater: %s", ex)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Alsavo Pro config entry."""
    _LOGGER.info("Unloading Alsavo Pro heater: %s", entry.data.get(CONF_NAME))

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.info("Alsavo Pro heater unloaded successfully.")
    else:
        _LOGGER.warning("Failed to unload Alsavo Pro heater.")

    return unload_ok


class AlsavoProDataCoordinator(DataUpdateCoordinator):
    """Coordinator to manage Alsavo Pro data fetching."""

    def __init__(self, hass: HomeAssistant, device: AlsavoPro) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="AlsavoProDataCoordinator",
            update_interval=timedelta(seconds=15),
        )
        self.device = device

    async def _async_update_data(self):
        """Fetch data from Alsavo Pro device."""
        _LOGGER.debug("Updating Alsavo Pro device data.")
        try:
            async with async_timeout.timeout(10):
                await self.device.update()
                _LOGGER.debug("Data update successful.")
                return self.device
        except Exception as ex:
            _LOGGER.exception("Error updating Alsavo Pro data: %s", ex)
            raise UpdateFailed("Failed to update Alsavo Pro data") from ex
