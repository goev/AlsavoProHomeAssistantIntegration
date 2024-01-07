"""Constants for Alsavo Pro pool heater integration."""

SERIAL_NO = "serial_no"
DOMAIN = "alsavopro"

POWER_MODE_MAP = {
    0: 'Silent',
    1: 'Smart',
    2: 'Powerful'
}
# Static mapping of operating modes to config keys
MODE_TO_CONFIG = {0: 2,  # Cool
                  1: 1,  # Heat
                  2: 3}  # Auto

# Errors
NO_WATER_FLUX = "No water flux or water flow switch failure.\n\r"
WATER_TEMP_TOO_LOW = "Water temperature (T2) too low protection under cooling mode.\n\r"

# Max retries
MAX_UPDATE_RETRIES = 10
MAX_SET_CONFIG_RETRIES = 10
