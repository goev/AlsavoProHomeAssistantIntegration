# Alsavo Pro / Swim & Fun / Artic Pro / Zealux ++ pool heatpump

Custom component for controlling pool heatpumps that uses the Alsavo Pro app in Home Assistant.

## Install
#### Manually
In Home Assistant, create a folder under *custom_components* named *AlsavoPro* and copy all the content of this project to that folder.
Restart Home Assistant and go to *Devices and Services* and press *+Add integration*.
Search for *AlsavoPro* and add it.
#### HACS Custom Repository
In HACS, add a custom repository and use https://github.com/laurensdehoorne/AlsavoProHomeAssistantIntegration
Download from HACS.
Restart Home Assistant and go to *Devices and Services* and press *+Add integration*.
Search for *AlsavoPro* and add it.

## Configuration
You must now choose a name for the device. The serial number for the heat pump can be found in the Alsavo Pro app by logging in to the heat pump and pressing the Alsavo Pro-logo in the upper right corner.
Password is the same as the one you logged into the Alsavo Pro app with.

Ip-address and port can be one of two:
- If you want to use the cloud, set IP-address to 47.254.157.150 and port to 51192.
- If you want to bypass the cloud, enter the heat pumps ip-address and use port 1194.

## Parameter setting
To access Alsavo Pro heat pump parameters, click "Parameter" in the app and enter password 0757. Key settings include water pump operating modes (P03), input calibration, temperature units, and system diagnostics. These settings allow control over water pump behavior (constant/compressor-dependent) and troubleshooting

## Alarm codes

The integration exposes four alarm code sensors (`alarm_code_1` through `alarm_code_4`) that reflect the raw values of the pump's status registers. The `errors` attribute decodes all active alarms into human-readable messages.

### EE codes (Electrical/Component) — registers 48 & 49

| Code | Malfunction |
|------|-------------|
| EE01 | High pressure failure |
| EE02 | Low pressure failure |
| EE03 | Water flow failure |
| EE04 | Water temperature overheating protection (heating mode) |
| EE05 | Exhaust temperature too high |
| EE06 | Controller malfunction or communication failure |
| EE07 | Compressor current protection |
| EE08 | Communication failure (controller ↔ PCB) |
| EE09 | Communication failure (PCB ↔ driver board) |
| EE10 | VDC voltage too high protection |
| EE11 | IPM module protection |
| EE12 | VDC voltage too low protection |
| EE13 | Input current too strong protection |
| EE14 | IPM module thermal circuit abnormal |
| EE15 | IPM module temperature too high protection |
| EE16 | PFC module protection |
| EE17 | DC fan failure |
| EE18 | PFC module thermal circuit abnormal |
| EE19 | PFC module high temperature protection |
| EE20 | Input power failure |
| EE21 | Software control failure |
| EE22 | Current detection circuit failure |
| EE23 | Compressor start failure |
| EE24 | Ambient temperature sensor failure (driving board) |
| EE25 | Compressor phase failure |
| EE26 | 4-way valve reversal failure |
| EE27 | EEPROM data reading failure |
| EE28 | Inter-chip communication failure (main control board) |

### PP codes (Protection/Sensor) — register 50

| Code | Malfunction |
|------|-------------|
| PP01 | Inlet water temperature sensor failure |
| PP02 | Outlet water temperature sensor failure |
| PP03 | Heating coil pipe sensor failure |
| PP04 | Gas return sensor failure |
| PP05 | Ambient temperature sensor failure |
| PP06 | Exhaust temperature sensor failure |
| PP07 | Anti-freezing protection (winter) |
| PP08 | Low ambient temperature protection |
| PP10 | Coil pipe temperature too high protection (cooling mode) |
| PP11 | Water temperature (T2) too low protection (cooling mode) |

## Climate

The integration exposes a climate entity with the following HVAC modes:

| Mode | Description |
|------|-------------|
| Heat | Heating mode |
| Cool | Cooling mode |
| Auto | Automatic mode (heat or cool as needed) |
| Off  | Power off |

Preset modes control fan/compressor power: **Silent**, **Smart**, **Powerful**.

## Sensors

### Temperature sensors

| Sensor | Description |
|--------|-------------|
| Water In | Inlet water temperature |
| Water Out | Outlet water temperature |
| Ambient | Ambient air temperature |
| Cold pipe | Cold pipe temperature |
| Heating pipe | Heating pipe temperature |
| IPM module | IPM module temperature |
| Exhaust temperature | Exhaust temperature |
| Compressor input temperature | Compressor input temperature |
| Heating max temperature | Maximum allowed heating setpoint |
| Cooling min temperature | Minimum allowed cooling setpoint |
| Defrost in temperature | Temperature threshold to start defrost |
| Defrost out temperature | Heating pipe temperature to end defrost |
| Water temperature calibration | Offset applied to all temperature readings |
| Heating mode target | Heating setpoint |
| Cooling mode target | Cooling setpoint |
| Auto mode target | Auto mode setpoint |

### Operational sensors

| Sensor | Description |
|--------|-------------|
| Fan speed | Fan speed in RPM |
| Compressor | Compressor current (A) |
| Compressor running frequency | Compressor frequency (Hz) |
| Compressor speed setting | 0=off, 1=P1 40Hz … 5=P5 82Hz |
| EEV opening | Electronic exhaust valve opening (0–450) |
| Frequency limit code | Active frequency limit code |
| System status code | System status code |
| System running code | 3=heating, 2=defrost |
| Device status code | Device status code |

### Config/diagnostic sensors

| Sensor | Description |
|--------|-------------|
| Power mode | 0=Silent, 1=Smart, 2=Powerful |
| Manual frequency setting | Manual compressor frequency (debug mode) |
| Manual EEV setting | Manual EEV setting (debug mode) |
| Manual fan speed setting | Manual fan speed (debug mode) |
| Defrost in time | Minimum time between defrost cycles (minutes) |
| Defrost out time | Maximum defrost duration (minutes) |
| Hot over | High temperature threshold |
| Cold over | Low temperature threshold |
| Current time | Device clock (hi byte=hours, lo byte=minutes) |
| Timer on time | Scheduled power-on time |
| Timer off time | Scheduled power-off time |
| Device type | Device type code |
| Main board HW revision | Hardware revision |
| Main board SW revision | Software revision |
| Manual HW code | Manual hardware code |
| Manual SW code | Manual software code |

### Alarm sensors

| Sensor | Description |
|--------|-------------|
| Alarm code 1–4 | Raw alarm register values (registers 48–51) |
| Error messages | Decoded human-readable alarm messages |

## Changelog

### 1.0.4
- Added Auto HVAC mode (maps to pump's internal auto mode)
- Added 18 new sensors: compressor input temp, EEV opening, compressor speed, device status code, heating max/cooling min temps, manual settings, defrost config, timer config, and more
- Fixed `ClimateEntityFeature.TURN_ON`/`TURN_OFF` missing from supported features (required in HA 2024.2+)
- Fixed `hvac_mode` returning `None` for unknown operating modes, now falls back to `HVACMode.OFF`
- Fixed `AlsavoProErrorSensor` missing `available` property, entity now correctly reflects online/offline state
- Removed unused imports in `climate.py` and `sensor.py`

### 1.0.3
- Full alarm code decoding for all EE (EE01–EE28) and PP (PP01–PP11) fault codes across registers 48–50

### 1.0.2
- Fixed `set_config` recursive retry replaced with iterative loop to prevent stack overflow and stale `_online` state
- Fixed `is_online` now correctly reflects live connection state instead of stale data presence
- Fixed `Payload.get_value` off-by-one bounds check

### 1.0.1
- Fixed `NoneType object is not subscriptable` crash when pump is temporarily offline during auth challenge
- Fixed `unpack requires a buffer of X bytes` error when receiving truncated UDP packets
- Added 2-second delay between update retries so the pump has time to recover when briefly offline

## AlsavoCtrl
This code is very much based on AlsavoCtrl: https://github.com/strandborg/AlsavoCtrl
