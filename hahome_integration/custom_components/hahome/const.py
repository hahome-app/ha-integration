"""Constants for the HAHome integration."""

DOMAIN = "hahome"
APP_ID = "io.hahome.app"

# Config keys
CONF_WEBHOOK_ID = "webhook_id"
CONF_DEVICE_NAME = "device_name"
CONF_TRIGGERS = "triggers"

# Trigger types — quick
TRIGGER_MOTION = "motion"
TRIGGER_DOOR = "door"
TRIGGER_BATTERY = "battery"
TRIGGER_UNAVAILABLE = "unavailable"

# Trigger types — advanced
TRIGGER_STATE = "state"
TRIGGER_NUMERIC_STATE = "numeric_state"

# Storage
STORAGE_KEY = "hahome.devices"
STORAGE_VERSION = 1