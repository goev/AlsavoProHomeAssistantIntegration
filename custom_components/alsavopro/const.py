"""Constants for Alsavo Pro pool heater integration."""

SERIAL_NO = "serial_no"
DOMAIN = "alsavopro"

# Power mode labels
POWER_MODE_MAP = {
    0: "Silent",
    1: "Smart",
    2: "Powerful"
}

# Static mapping of operating modes to config keys
MODE_TO_CONFIG = {
    0: 2,  # Cool
    1: 1,  # Heat
    2: 3   # Auto
}

# Retry limits
MAX_UPDATE_RETRIES = 10
MAX_SET_CONFIG_RETRIES = 10

# Raw error messages from the device
NO_WATER_FLUX = "No water flux or water flow switch failure.\n\r"
WATER_TEMP_TOO_LOW = "Water temperature (T2) too low protection under cooling mode.\n\r"

# Mapping from raw messages to translation keys
ERROR_TRANSLATION_KEYS = {
    NO_WATER_FLUX.strip(): "no_water_flux",
    WATER_TEMP_TOO_LOW.strip(): "water_temp_too_low",
}
