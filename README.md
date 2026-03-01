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

## AlsavoCtrl
This code is very much based on AlsavoCtrl: https://github.com/strandborg/AlsavoCtrl
