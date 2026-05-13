# Changelog

## [1.0.6] - 2026-05-13

### Fixed
- Aligned auth challenge-response MD5 hash with the reference C++ implementation: token bytes are now packed little-endian (matching native x86 byte order used by the pump server)
- Expanded `clientToken` entropy from 16-bit to full 32-bit random value, matching the reference implementation

## [1.0.5] - 2026-05-13

### Fixed
- Replaced deprecated `async_timeout` package with stdlib `asyncio.timeout` (HA 2024.x compatibility)
- Replaced deprecated `async_forward_entry_unload` (called twice) with `async_forward_entry_unloads` accepting a list
- Removed deprecated `CONNECTION_CLASS` from `ConfigFlow`
- Fixed `OptionsFlowHandler` constructor — HA no longer passes `config_entry`; moved `async_get_options_flow` as a `@staticmethod` inside `ConfigFlow`
- Fixed `MissingPasswordValue` exception being raised but never caught in `async_step_user`
- Replaced `asyncio.get_event_loop()` (deprecated in Python 3.10+) with `asyncio.get_running_loop()` in `UDPClient`
- Fixed absolute import `from custom_components.alsavopro.const import ...` to relative `from .const import ...`
- Renamed `async_add_devices` to `async_add_entities` in sensor setup
- Replaced bare `"°C"` strings with `UnitOfTemperature.CELSIUS` constant in sensor definitions
- Fixed log strings with double closing parentheses in `AlsavoPyCtrl`
- Removed unused imports (`CONF_PASSWORD`, `CONF_IP_ADDRESS`, `CONF_PORT`, `CONF_NAME`) from `climate.py`
- Fixed `manifest.json` version to match released version

## [1.0.4] - 2024

### Added
- Additional sensor entities (EEV opening, compressor speed, device status, min/max temperatures, manual settings)

## [1.0.3] - 2024

### Added
- Alarm code registers 48, 49, 50 with full error descriptions
- Error messages sensor aggregating all active alarm codes

## [1.0.2] - 2024

### Added
- Initial HACS release
- Climate entity with heat, cool, auto, and off modes
- Preset modes: Silent, Smart, Powerful
- Temperature sensors: water in, water out, ambient, cold pipe, heating pipe, IPM module, exhaust
- Config sensors: heating/cooling/auto target temperatures, power mode
- Compressor current, frequency, and fan speed sensors
