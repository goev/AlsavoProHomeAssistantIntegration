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

# Alarm code bit maps per status register
ALARM_REGISTER_48 = {
    0x0001: "EE01: High pressure failure",
    0x0002: "EE02: Low pressure failure",
    0x0004: "EE03: Water flow failure",
    0x0008: "EE04: Water temperature overheating protection (heating mode)",
    0x0010: "EE05: Exhaust temperature too high",
    0x0020: "EE06: Controller malfunction or communication failure",
    0x0040: "EE07: Compressor current protection",
    0x0080: "EE08: Communication failure (controller ↔ PCB)",
    0x0100: "EE09: Communication failure (PCB ↔ driver board)",
    0x0200: "EE10: VDC voltage too high protection",
    0x0400: "EE11: IPM module protection",
    0x0800: "EE12: VDC voltage too low protection",
    0x1000: "EE13: Input current too strong protection",
    0x2000: "EE14: IPM module thermal circuit abnormal",
    0x4000: "EE15: IPM module temperature too high protection",
    0x8000: "EE16: PFC module protection",
}

ALARM_REGISTER_49 = {
    0x0001: "EE17: DC fan failure",
    0x0002: "EE18: PFC module thermal circuit abnormal",
    0x0004: "EE19: PFC module high temperature protection",
    0x0008: "EE20: Input power failure",
    0x0010: "EE21: Software control failure",
    0x0020: "EE22: Current detection circuit failure",
    0x0040: "EE23: Compressor start failure",
    0x0080: "EE24: Ambient temperature sensor failure (driving board)",
    0x0100: "EE25: Compressor phase failure",
    0x0200: "EE26: 4-way valve reversal failure",
    0x0400: "EE27: EEPROM data reading failure",
    0x0800: "EE28: Inter-chip communication failure (main control board)",
}

ALARM_REGISTER_50 = {
    0x0001: "PP01: Inlet water temperature sensor failure",
    0x0002: "PP02: Outlet water temperature sensor failure",
    0x0004: "PP03: Heating coil pipe sensor failure",
    0x0008: "PP04: Gas return sensor failure",
    0x0010: "PP05: Ambient temperature sensor failure",
    0x0020: "PP06: Exhaust temperature sensor failure",
    0x0040: "PP07: Anti-freezing protection (winter)",
    0x0080: "PP08: Low ambient temperature protection",
    0x0200: "PP10: Coil pipe temperature too high protection (cooling mode)",
    0x0400: "PP11: Water temperature (T2) too low protection (cooling mode)",
}

# Max retries
MAX_UPDATE_RETRIES = 10
MAX_SET_CONFIG_RETRIES = 10
