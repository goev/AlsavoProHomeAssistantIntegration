"""Adds config flow for AlsavoPro pool heater integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_NAME,
    CONF_IP_ADDRESS,
    CONF_PORT,
)

from .const import (
    SERIAL_NO,
    DOMAIN,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(SERIAL_NO): str,
        vol.Required(CONF_IP_ADDRESS): str,
        vol.Required(CONF_PORT): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Alsavo Pro pool heater integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            name = user_input[CONF_NAME]
            serial_no = user_input[SERIAL_NO]
            ip_address = user_input[CONF_IP_ADDRESS]
            port_no = user_input[CONF_PORT]
            password = user_input[CONF_PASSWORD].replace(" ", "")

            # Serial number is the only stable identifier for the device.
            await self.async_set_unique_id(serial_no)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"{name} ({serial_no})",
                data={
                    CONF_NAME: name,
                    SERIAL_NO: serial_no,
                    CONF_IP_ADDRESS: ip_address,
                    CONF_PORT: port_no,
                    CONF_PASSWORD: password,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            new_password = user_input.get(CONF_PASSWORD, "").replace(" ", "")
            if new_password:
                new_data = {**self._entry.data, CONF_PASSWORD: new_password}
                self.hass.config_entries.async_update_entry(self._entry, data=new_data)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_PASSWORD): str,
            }),
        )
