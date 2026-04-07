# HAHome Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Send push notifications from Home Assistant directly to your [HAHome](https://hahome.io) app on iPhone and iPad.

## How it works

HAHome registers itself with Home Assistant as a mobile device (via the standard `mobile_app` platform). This integration detects your registered HAHome devices and lets you configure notification triggers — no server, no extra accounts, no complex setup.

Notifications are delivered via Home Assistant's built-in mobile_app platform — no additional server or account required.

```
Home Assistant → HAHome Integration → notify.mobile_app_* → APNs → HAHome on iPhone
```

## Requirements

- [HAHome](https://hahome.io) installed on your iPhone or iPad
- Home Assistant 2024.1 or later
- The HAHome app connected to your Home Assistant instance

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the three dots → **Custom repositories**
4. Add `https://github.com/hahome-app/ha-integration` as an **Integration**
5. Search for **HAHome** and install it
6. Restart Home Assistant

### Manual

1. Download the latest release
2. Copy the `custom_components/hahome` folder into your HA `config/custom_components/` directory
3. Restart Home Assistant

## Setup

1. Open the HAHome app on your iPhone and complete the Home Assistant connection in the app settings — this registers your device automatically
2. In Home Assistant go to **Settings → Devices & Services → Add Integration**
3. Search for **HAHome**
4. Select your device from the dropdown
5. Press **Submit**

Your device is now set up. Open the integration options to add notification triggers.

## Notification triggers

After setup, press **Configure** on the integration to add triggers.

### Quick triggers

| Trigger | Description |
|---|---|
| Motion detected | Fires when a motion sensor turns on |
| Door / window opened | Fires when a door or window sensor opens |
| Battery low | Fires when a battery sensor drops below a threshold |
| Device unavailable | Fires when any entity becomes unavailable |

### Advanced triggers

| Trigger | Description |
|---|---|
| State change | Fires when an entity changes state, optionally filtered by from/to value |
| Numeric threshold | Fires when a numeric sensor crosses above or below a value |

Each trigger has a configurable **title** and **message** for the notification.

## Using in automations

Once set up, HAHome devices are also available as standard notify services in automations:

```yaml
action:
  - service: notify.mobile_app_hahome_johns_iphone
    data:
      title: "Motion detected"
      message: "Someone is at the front door"
```

## Troubleshooting

**Device not showing in dropdown**
Make sure you have opened HAHome and completed the Home Assistant connection. Then restart HA and try adding the integration again.

**Not receiving notifications**
- Check that HAHome has notification permissions in iOS Settings
- If running the app via Xcode (development), make sure your push worker is configured for the sandbox APNs environment
- Re-open HAHome and reconnect to HA to refresh the push token

**Config flow error**
Check Home Assistant logs at **Settings → System → Logs** and search for `hahome` for details.

## Links

- [HAHome website](https://hahome.io)
- [Report an issue](https://github.com/hahome-app/ha-integration/issues)
