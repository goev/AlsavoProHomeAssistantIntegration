# Alsavo Pro / Swim & Fun / Artic Pro / Zealux ++ pool heatpump

Custom component for controlling pool heatpumps that uses the Alsavo Pro app in Home Assistant.

**Warning:** This is made by someone with no previous knowledge of Python and no knowledge of Home Assistant framework. And one could argue that both is still the case. Use this at your own risk, and please take backups!

If some adult with the proper knowledge could improve this, and maybe make it installable with HACS, please feel free to do so! 

## Install
#### Manually
In Home Assistant, create a folder under *custom_components* named *AlsavoPro* and copy all the content of this project to that folder.
Restart Home Assistant and go to *Devices and Services* and press *+Add integration*.
Search for *AlsavoPro* and add it.
#### HACS Custom Repository
In HACS, add a custom repository and use https://github.com/goev/AlsavoProHomeAssistantIntegration
Download from HACS.
Restart Home Assistant and go to *Devices and Services* and press *+Add integration*.
Search for *AlsavoPro* and add it.

## Configuration
When adding the integration, you will be asked to choose a connection type:

### Cloud Connection
Connect via the Alsavo cloud server. You will need:
- **Device name**: Choose a name for the device
- **Serial number**: Found in the Alsavo Pro app by logging in to the heat pump and pressing the Alsavo Pro logo in the upper right corner
- **Password**: The same password you use to log into the Alsavo Pro app

### Local Connection
Connect directly to your heat pump on the local network. You will need:
- **Device name**: Choose a name for the device
- **Serial number**: Found in the Alsavo Pro app (see above)
- **IP-address**: The local IP address of your heat pump
- **Port**: Use 1194 for local connections
- **Password**: The same password you use to log into the Alsavo Pro app

### Editing an existing connection

Open **Settings → Devices & services → AlsavoPro**, then select **Reconfigure**
from the entry's menu. You can edit the device name, serial number, address,
port and password without deleting the integration. Leave the password blank
to retain it. Saving reloads all platforms and keeps existing entity and device
identities so dashboards and automations remain linked. Only change the serial
number to correct the same pump, not to replace it with another device.

The form checks basic input validity; connection availability is checked by the
normal polling after reload. Reopen Reconfigure to correct unreachable details.

## Thermostat activity and icons

The climate entity reports actual activity separately from the selected
Heat/Cool/Auto mode. It reads shared pump data directly, so separate compressor
frequency and status sensor entities can remain disabled.

| System running code | Reported activity |
| --- | --- |
| 1 | Idle |
| 2 | Defrosting (documented in AlsavoCtrl; not verified on the reporting user's pump) |
| 3 | Heating, or Idle when compressor frequency is zero |
| 4 | Cooling, or Idle when compressor frequency is zero |
| Other values, including 5 | Unknown (no activity reported) |

Power off takes precedence, and unavailable pumps do not report activity.
Codes 1, 3 and 4 were observed by a user on one pump; other models may differ.
Code 5 has not been verified and is not assumed to indicate Auto activity.

The default climate icon is a pool thermometer. Presets use leaf (Silent),
brain (Smart), and flexed arm (Powerful) icons.

## Development checks

Run `python3 -m unittest discover -s tests -v` for dependency-free behavior checks.
These exercise actual methods with framework stand-ins; they do not replace
Home Assistant integration tests or live hardware testing.

## AlsavoCtrl
This code is very much based on AlsavoCtrl: https://github.com/strandborg/AlsavoCtrl
