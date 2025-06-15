"""Constants for Alsavo Pro pool heater integration."""

# Integration domain and unique identifiers
DOMAIN = "alsavopro"
SERIAL_NO = "serial_no"

# Mapping of power modes (int) to human-readable labels
POWER_MODE_MAP = {
    0: "Silent",
    1: "Smart",
    2: "Powerful"
}

# Mapping of mode indexes to Alsavo configuration keys
# These likely correspond to Cool, Heat, and Auto modes
MODE_TO_CONFIG = {
    0: 2,  # Cool mode
    1: 1,  # Heat mode
    2: 3   # Auto mode
}

# Device-reported error messages
NO_WATER_FLUX = "No water flux or water flow switch failure.\n\r"
WATER_TEMP_TOO_LOW = "Water temperature (T2) too low protection under cooling mode.\n\r"

# Retry limits for updating or configuring the device
MAX_UPDATE_RETRIES = 10
MAX_SET_CONFIG_RETRIES = 10
