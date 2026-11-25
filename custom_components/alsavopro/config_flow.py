"""Adds config flow for AlsavoPro pool heater integration."""
import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_NAME,
    CONF_IP_ADDRESS,
    CONF_PORT
)

from .const import (
    SERIAL_NO,
    DOMAIN,
    CONNECTION_TYPE,
    CONNECTION_TYPE_CLOUD,
    CONNECTION_TYPE_LOCAL,
    CLOUD_IP,
    CLOUD_PORT,
    DEFAULT_LOCAL_PORT,
)

# _LOGGER = logging.getLogger(__name__)

CONNECTION_TYPE_SCHEMA = vol.Schema(
    {
        vol.Required(CONNECTION_TYPE, default=CONNECTION_TYPE_CLOUD): vol.In(
            [CONNECTION_TYPE_CLOUD, CONNECTION_TYPE_LOCAL]
        ),
    }
)

CLOUD_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(SERIAL_NO): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

LOCAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(SERIAL_NO): str,
        vol.Required(CONF_IP_ADDRESS): str,
        vol.Required(CONF_PORT, default=DEFAULT_LOCAL_PORT): str,
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
        if entry.data[SERIAL_NO] == serial_no:
            raise AlreadyConfigured("A device with this serial number already exists.")

    # Additional validations (if any) go here...


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alsavo Pro pool heater integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_reconfigure(self, user_input=None):
        """Edit connection details while retaining existing entity identities."""
        entry = self._get_reconfigure_entry()
        errors = {}
        if user_input is not None:
            data = {**entry.data, **user_input}
            data[CONF_NAME] = data[CONF_NAME].strip()
            data[SERIAL_NO] = data[SERIAL_NO].strip()
            data[CONF_IP_ADDRESS] = data[CONF_IP_ADDRESS].strip()
            # An empty password field retains the stored password.
            data[CONF_PASSWORD] = (
                user_input.get(CONF_PASSWORD, "").replace(" ", "")
                or entry.data[CONF_PASSWORD]
            )
            try:
                if not data[CONF_NAME] or not data[CONF_IP_ADDRESS]:
                    raise ValueError
                if not data[SERIAL_NO].isdigit() or not 0 < int(data[SERIAL_NO]) < 2**64:
                    raise ValueError
                if not 1 <= int(data[CONF_PORT]) <= 65535:
                    raise ValueError
                data[CONF_PORT] = str(data[CONF_PORT])
            except (ValueError, TypeError):
                errors["base"] = "invalid_details"
            else:
                if any(
                    other.entry_id != entry.entry_id
                    and other.data.get(SERIAL_NO) == data[SERIAL_NO]
                    for other in self.hass.config_entries.async_entries(DOMAIN)
                ):
                    errors["base"] = "already_configured"
                else:
                    data.setdefault(
                        "entity_identity",
                        f"{entry.data[CONF_NAME]}_{entry.data[SERIAL_NO]}",
                    )
                    data.setdefault("device_identity", entry.data[SERIAL_NO])
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates=data,
                        title=f"{data[CONF_NAME]}-{data[SERIAL_NO]}",
                    )
        values = user_input if user_input is not None else entry.data
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=values.get(CONF_NAME, "")): str,
                vol.Required(SERIAL_NO, default=values.get(SERIAL_NO, "")): str,
                vol.Required(CONF_IP_ADDRESS, default=values.get(CONF_IP_ADDRESS, "")): str,
                vol.Required(CONF_PORT, default=str(values.get(CONF_PORT, DEFAULT_LOCAL_PORT))): str,
                vol.Optional(CONF_PASSWORD): str,
            }),
            errors=errors,
        )

    async def async_step_user(self, user_input=None):
        """Handle the initial step: choose connection type."""
        if user_input is not None:
            if user_input[CONNECTION_TYPE] == CONNECTION_TYPE_CLOUD:
                return await self.async_step_cloud()
            return await self.async_step_local()

        return self.async_show_form(
            step_id="user",
            data_schema=CONNECTION_TYPE_SCHEMA,
        )

    async def async_step_cloud(self, user_input=None):
        """Handle cloud connection configuration."""
        errors = {}

        if user_input is not None:
            try:
                name = user_input[CONF_NAME]
                serial_no = user_input[SERIAL_NO]
                password = user_input[CONF_PASSWORD].replace(" ", "")
                await validate_input(self.hass, name, serial_no, CLOUD_IP, CLOUD_PORT, password)
                unique_id = f"{name}-{serial_no}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=unique_id,
                    data={CONF_NAME: name,
                          SERIAL_NO: serial_no,
                          CONF_IP_ADDRESS: CLOUD_IP,
                          CONF_PORT: CLOUD_PORT,
                          CONF_PASSWORD: password},
                )

            except AlreadyConfigured:
                return self.async_abort(reason="already_configured")
            except CannotConnect:
                errors["base"] = "connection_error"
            except MissingNameValue:
                errors["base"] = "missing_name"

        return self.async_show_form(
            step_id="cloud",
            data_schema=CLOUD_SCHEMA,
            errors=errors,
        )

    async def async_step_local(self, user_input=None):
        """Handle local connection configuration."""
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
            step_id="local",
            data_schema=LOCAL_SCHEMA,
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class AlreadyConfigured(exceptions.HomeAssistantError):
    """Error to indicate host is already configured."""


class MissingNameValue(exceptions.HomeAssistantError):
    """Error to indicate name is missing."""


class MissingPasswordValue(exceptions.HomeAssistantError):
    """Error to indicate name is missing."""
