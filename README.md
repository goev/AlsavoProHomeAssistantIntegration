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
You must choose a name for the device. The serial number for the heat pump can be found in the Alsavo Pro app by logging in to the heat pump and pressing the Alsavo Pro-logo in the upper right corner.
Password is the same as the one you logged into the Alsavo Pro app with.

For IP-address, enter the heat pump's local IP address on your network, and use port `1194`. The integration talks directly to the pump over UDP — no cloud connection is involved.

> **Note:** Earlier versions of this README documented a cloud-relay option using a public IP (`47.254.157.150:51192`). That cloud endpoint is no longer reachable (the GalaxyWind / Alsavo regional cloud servers appear to be retired for some regions), and the integration has always worked fine against the pump's LAN IP. The cloud option is no longer recommended or supported.

## Parameter setting
To access Alsavo Pro heat pump parameters, click "Parameter" in the app and enter password 0757. Key settings include water pump operating modes (P03), input calibration, temperature units, and system diagnostics. These settings allow control over water pump behavior (constant/compressor-dependent) and troubleshooting.

## Troubleshooting

### "Offline" in the app but works in HA
The official Alsavo Pro app routes everything through the GalaxyWind cloud (`*.ice.galaxywind.com`). This integration uses direct UDP on your LAN and doesn't need the cloud, so "offline in app, online in HA" is normal — and means local control is healthy.

### Intermittent HA timeouts or slow updates
If the pump can't reach its cloud server, its WiFi module enters a retry loop that can starve local UDP responses. The European/Australian/Brazilian dispatcher (`47.88.188.100`) currently doesn't respond, and that same IP is hardcoded as a fallback inside the pump firmware — so even DNS-blocking the hostname isn't enough on its own.

If you see slow or intermittent local responses, add a firewall rule on the IoT network that **REJECTs** (not drops) outbound traffic from the pump to:

- `47.88.188.100` (hardcoded EU/AU/BR fallback)
- `*.ice.galaxywind.com` if your firewall supports DNS-based rules

Use REJECT, not DROP — REJECT replies with "unreachable" immediately so the pump gives up fast, while DROP makes it hang on slow timeouts (same problem you're trying to solve). After applying the rule, power-cycle the pump so it discards its current retry state.

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

The set of available modes is filtered per device type — single-mode units only show Heat, FixCh/FreqCh units show Heat + Cool, FreqAll/FixAll show all three plus Auto.

Preset modes control fan/compressor power: **Silent**, **Smart**, **Powerful**. Preset selection is only exposed for variable-frequency devices.

## Controls (writeable settings)

Beyond the climate entity, the integration also exposes installer-level settings that the official Android app lets you tune. After a setting is changed, the pump's new state is reflected in HA after ~5 seconds.

### Numbers

| Entity | Register | Range | Step |
|---|---|---|---|
| Defrost in temperature | 9 | -30 … 0 °C | 1 |
| Defrost out temperature | 10 | 2 … 30 °C | 1 |
| Defrost in time | 12 | 30 … 90 min | 1 |
| Defrost out time | 13 | 1 … 12 min | 1 |
| Water temperature compensation | 11 | -9.0 … 9.0 °C | 0.1 |

### Switches

| Entity | Register | Notes |
|---|---|---|
| Timer on enabled | config_sys1 bit 2 | Enables the scheduled daily power-on at *Timer on time* |
| Timer off enabled | config_sys1 bit 7 | Enables the scheduled daily power-off at *Timer off time* |
| Pump continuous run | config_sys1 bit 3 | Water circulation pump runs continuously (vs. cycling with the compressor) |

### Times

| Entity | Register | Encoding |
|---|---|---|
| Timer on time | 33 | HH:MM picker (stored as `hour << 8 \| minute`) |
| Timer off time | 34 | same |

### Tuning for winter operation

If you keep the heat pump running through winter, the factory defrost defaults often aren't aggressive enough — ice can build up faster than the cycle clears it. Reasonable starting points for Northwest-European climate (-5 … +5 °C ambient):

| Setting | Default | Winter |
|---|---|---|
| Defrost in temp | -7 °C | **-5 °C** (trigger sooner) |
| Defrost in time | 40 min | **30 min** (react faster) |
| Defrost out temp | 20 °C | **13 °C** (don't overheat the coil) |
| Defrost out time | 12 min | **8 min** |
| Pump continuous run | off | **on** (water keeps circulating through the heat exchanger between cycles) |

Below ~-7 °C ambient the air-source COP collapses; no defrost setting can compensate, and the practical answer is to winterize the pool and drain the heat exchanger.

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
| Hot over | High-temperature hysteresis offset (signed) |
| Cold over | Low-temperature hysteresis offset (signed, can be negative) |
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


## AlsavoCtrl
This code is very much based on AlsavoCtrl: https://github.com/strandborg/AlsavoCtrl
