"""Alsavo Pro pool heat pump integration."""
import logging
from datetime import timedelta

import async_timeout
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


async def async_setup(hass, config):
    """Perform setup for the Alsavo Pro integration."""
    _LOGGER.debug("async_setup called for Alsavo Pro integration.")
    return True


async def async_setup_entry(hass, entry):
    """Set up the Alsavo Pro heater from a config entry."""
    _LOGGER.info("Setting up Alsavo Pro heater: %s", entry.data.get(CONF_NAME))

    try:
        name = entry.data[CONF_NAME]
        serial_no = entry.data[SERIAL_NO]
        ip_address = entry.data[CONF_IP_ADDRESS]
        port_no = entry.data[CONF_PORT]
        password = entry.data[CONF_PASSWORD]

        # Initialize the data handler
        data_handler = AlsavoPro(name, serial_no, ip_address, port_no, password)
        await data_handler.update()
        _LOGGER.debug("Initial data fetched for Alsavo Pro: %s", name)

        # Create and store the data coordinator
        data_coordinator = AlsavoProDataCoordinator(hass, data_handler)
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        hass.data[DOMAIN][entry.entry_id] = data_coordinator

        # Forward entries to sensor and climate platforms
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "climate"])
        _LOGGER.info("Alsavo Pro heater setup complete for %s", name)

        return True
    except Exception as ex:
        _LOGGER.error("Error setting up Alsavo Pro heater: %s", ex)
        return False


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    _LOGGER.info("Unloading Alsavo Pro heater: %s", config_entry.data.get(CONF_NAME))

    unload_ok = True
    unload_ok &= await hass.config_entries.async_forward_entry_unload(
        config_entry, "climate"
    )
    unload_ok &= await hass.config_entries.async_forward_entry_unload(
        config_entry, "sensor"
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id, None)
        _LOGGER.info("Alsavo Pro heater unloaded successfully.")
    else:
        _LOGGER.warning("Failed to unload Alsavo Pro heater.")

    return unload_ok


class AlsavoProDataCoordinator(DataUpdateCoordinator):
    """Custom DataUpdateCoordinator for Alsavo Pro."""

    def __init__(self, hass, data_handler):
        """Initialize the Alsavo Pro Data Coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="AlsavoPro",
            update_interval=timedelta(seconds=15),
        )
        self.data_handler = data_handler

    async def _async_update_data(self):
        """Fetch updated data from the Alsavo Pro device."""
        _LOGGER.debug("Fetching updated data from Alsavo Pro device.")
        try:
            async with async_timeout.timeout(10):
                await self.data_handler.update()
                _LOGGER.debug("Successfully updated data for Alsavo Pro.")
                return self.data_handler
        except Exception as ex:
            _LOGGER.error("Error fetching data from Alsavo Pro device: %s", ex)
            raise UpdateFailed("Failed to update Alsavo Pro data.") from ex
