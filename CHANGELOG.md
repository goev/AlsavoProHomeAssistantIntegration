# Changelog

## [1.1.0] - 2026-05-17

### Added
- **`number` platform** — five writeable installer settings, with min/max taken directly from the official Android app:
  - Defrost in temperature (-30 … 0 °C)
  - Defrost out temperature (2 … 30 °C)
  - Defrost in time (30 … 90 min)
  - Defrost out time (1 … 12 min)
  - Water temperature compensation (-9.0 … 9.0 °C, step 0.1)
- **`switch` platform** — three boolean flags on config register 4:
  - Timer on enabled
  - Timer off enabled
  - Pump continuous run (water circulation mode)
- **`time` platform** — daily timer schedule:
  - Timer on time (HH:MM)
  - Timer off time (HH:MM)
- HVAC modes are now device-type-aware: each Alsavo device type (FreqAll, Single, FixCh, FreqCh, FixAll) only exposes the modes its hardware supports
- 5-second follow-up refresh after every control command — UI reflects the settled pump state without waiting for the next 60 s poll

### Fixed
- **Set-target/mode/preset writes no longer silently dropped.** The pump only commits config writes on a freshly authenticated session; the persistent-session refactor briefly broke this by reusing a CSID/DSID across writes. Writes now always re-handshake; reads keep reusing the session.
- **`Cold over` sensor showed `65516` instead of `-20`.** The register is a signed 16-bit hysteresis offset but was being read as unsigned. Both `Hot over` and `Cold over` now use the signed interpretation.
- **First query after a write no longer wastes 2 s on a stale-packet retry.** The pump invalidates the session right after a config write; the integration now disconnects proactively so the follow-up read does a fast handshake instead of going through the bad-response → sleep → re-auth path.
- **Startup no longer fails permanently if the pump is briefly unreachable.** Up to 5 consecutive polling failures are tolerated before entities go unavailable.
- **Empty/truncated response packets no longer return zeros silently** — `query_all` now validates the response carries both a status and config section and raises `ConnectionError` otherwise.
- Pre-existing `_followup_cancel` `TypeError` on the second consecutive command (the handle was being called instead of `.cancel()`-ed).
- Follow-up refresh timer is now properly cancelled on config-entry unload, so reloading the integration mid-window no longer leaves a dangling timer firing against a torn-down coordinator.

### Changed
- Persistent UDP session across the 60 s poll interval (reads); fresh handshake per write. Reduces protocol overhead from ~56 ms per call to ~10 ms per call for reads.
- Dropped dead code: `AlsavoSocketCom.send_packet`, `AlsavoSocketCom.send`, `UDPClient.send`, `UDPClient.SimpleClientProtocol` — only the request/response path is used now.

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
