"""Adds config flow for AlsavoPro pool heater integration."""
import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.core import callback
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_NAME,
    CONF_IP_ADDRESS,
    CONF_PORT
)

from .const import (
    SERIAL_NO,
    DOMAIN
)

# _LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(SERIAL_NO): str,
        vol.Required(CONF_IP_ADDRESS): str,
        vol.Required(CONF_PORT): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: core.HomeAssistant, name, serial_no, ip_address, port_no, password):
    """Validate the user input allows us to connect."""

    # Pre-validation for missing mandatory fields
    if not name:
        raise MissingNameValue("The 'name' field is required.")
    if not password:
        raise MissingPasswordValue("The 'password' field is required.")

    for entry in hass.config_entries.async_entries(DOMAIN):
        if any([
            entry.data[SERIAL_NO] == serial_no,
            entry.data[CONF_NAME] == name,
            entry.data[CONF_IP_ADDRESS] == ip_address,
            entry.data[CONF_PORT] == port_no
        ]):
            raise AlreadyConfigured("An entry with the given details already exists.")

    # Additional validations (if any) go here...


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alsavo Pro pool heater integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                name = user_input[CONF_NAME]
                serial_no = user_input[SERIAL_NO]
                ip_address = user_input[CONF_IP_ADDRESS]
                port_no = user_input[CONF_PORT]
                password = user_input[CONF_PASSWORD].replace(" ", "")
                await validate_input(self.hass, name, serial_no, ip_address, port_no, password)
                unique_id = f"{name}-{serial_no}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=unique_id,
                    data={CONF_NAME: name,
                          SERIAL_NO: serial_no,
                          CONF_IP_ADDRESS: ip_address,
                          CONF_PORT: port_no,
                          CONF_PASSWORD: password},
                )

            except AlreadyConfigured:
                return self.async_abort(reason="already_configured")
            except CannotConnect:
                errors["base"] = "connection_error"
            except MissingNameValue:
                errors["base"] = "missing_name"

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_PASSWORD): str,
            }),
        )


@callback
def async_get_options_flow(config_entry):
    return OptionsFlowHandler(config_entry)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class AlreadyConfigured(exceptions.HomeAssistantError):
    """Error to indicate host is already configured."""


class MissingNameValue(exceptions.HomeAssistantError):
    """Error to indicate name is missing."""


class MissingPasswordValue(exceptions.HomeAssistantError):
    """Error to indicate name is missing."""
