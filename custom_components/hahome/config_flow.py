"""Config flow for HAHome."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
)

from .const import (
    APP_ID,
    CONF_DEVICE_NAME,
    CONF_TRIGGERS,
    CONF_WEBHOOK_ID,
    DOMAIN,
    TRIGGER_STATE,
    TRIGGER_NUMERIC_STATE,
    TRIGGER_BATTERY,
    TRIGGER_UNAVAILABLE,
    TRIGGER_MOTION,
    TRIGGER_DOOR,
)

_LOGGER = logging.getLogger(__name__)

QUICK_TRIGGER_TYPES = {
    TRIGGER_MOTION: "Motion detected",
    TRIGGER_DOOR: "Door / window opened",
    TRIGGER_BATTERY: "Battery low",
    TRIGGER_UNAVAILABLE: "Device unavailable",
}

ADVANCED_TRIGGER_TYPES = {
    TRIGGER_STATE: "State change",
    TRIGGER_NUMERIC_STATE: "Numeric threshold",
}

ALL_TRIGGER_TYPES = {**QUICK_TRIGGER_TYPES, **ADVANCED_TRIGGER_TYPES}


def _get_hahome_devices(hass) -> dict[str, str]:
    """Return {webhook_id: title} for HAHome devices registered via mobile_app."""
    result: dict[str, str] = {}
    for entry in hass.config_entries.async_entries("mobile_app"):
        if entry.data.get("app_id") == APP_ID:
            webhook_id = entry.data.get("webhook_id")
            if webhook_id:
                result[webhook_id] = entry.title
    return result


class HAHomeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow: pick a registered HAHome device."""

    VERSION = 1

    def __init__(self) -> None:
        self._devices: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        self._devices = _get_hahome_devices(self.hass)

        if not self._devices:
            return await self.async_step_no_devices()

        errors: dict[str, str] = {}

        if user_input is not None:
            webhook_id = user_input[CONF_WEBHOOK_ID]
            device_name = self._devices[webhook_id]

            await self.async_set_unique_id(webhook_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=device_name,
                data={
                    CONF_WEBHOOK_ID: webhook_id,
                    CONF_DEVICE_NAME: device_name,
                },
            )

        device_options = [
            {"value": wid, "label": name}
            for wid, name in self._devices.items()
        ]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_WEBHOOK_ID): SelectSelector(
                        SelectSelectorConfig(options=device_options)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_no_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return await self.async_step_user()

        return self.async_show_form(
            step_id="no_devices",
            data_schema=vol.Schema({}),
            description_placeholders={
                "instructions": (
                    "Open HAHome on your iPhone and complete the Home Assistant "
                    "connection. The app registers itself automatically. "
                    "Then come back and press Submit."
                )
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HAHomeOptionsFlow:
        return HAHomeOptionsFlow()


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------

class HAHomeOptionsFlow(config_entries.OptionsFlow):
    """Options flow: manage notification triggers."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if not hasattr(self, "_triggers"):
            self._triggers = list(self.config_entry.options.get(CONF_TRIGGERS, []))

        if user_input is not None:
            action = user_input.get("action")
            if action == "add_trigger":
                return await self.async_step_pick_trigger_type()
            if action and action.startswith("remove_"):
                idx = int(action.removeprefix("remove_"))
                if 0 <= idx < len(self._triggers):
                    self._triggers.pop(idx)
                return self.async_create_entry(
                    title="", data={CONF_TRIGGERS: self._triggers}
                )
            return self.async_create_entry(
                title="", data={CONF_TRIGGERS: self._triggers}
            )

        remove_options = [
            {"value": f"remove_{i}", "label": f"Remove: {_describe_trigger(t)}"}
            for i, t in enumerate(self._triggers)
        ]

        actions = [
            {"value": "add_trigger", "label": "Add notification trigger"},
            *remove_options,
            {"value": "save", "label": "Save & close"},
        ]

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): SelectSelector(
                        SelectSelectorConfig(options=actions)
                    ),
                }
            ),
            description_placeholders={
                "device": self.config_entry.data.get(CONF_DEVICE_NAME, "HAHome"),
                "count": str(len(self._triggers)),
            },
        )

    async def async_step_pick_trigger_type(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Pick trigger category: quick or advanced."""
        if user_input is not None:
            t = user_input["type"]
            if t == TRIGGER_MOTION:
                return await self.async_step_quick_motion()
            if t == TRIGGER_DOOR:
                return await self.async_step_quick_door()
            if t == TRIGGER_BATTERY:
                return await self.async_step_quick_battery()
            if t == TRIGGER_UNAVAILABLE:
                return await self.async_step_quick_unavailable()
            if t == TRIGGER_STATE:
                return await self.async_step_trigger_state()
            if t == TRIGGER_NUMERIC_STATE:
                return await self.async_step_trigger_numeric()

        options = [
            {"value": k, "label": v}
            for k, v in ALL_TRIGGER_TYPES.items()
        ]

        return self.async_show_form(
            step_id="pick_trigger_type",
            data_schema=vol.Schema(
                {
                    vol.Required("type"): SelectSelector(
                        SelectSelectorConfig(options=options)
                    ),
                }
            ),
        )

    # ------------------------------------------------------------------
    # Quick triggers
    # ------------------------------------------------------------------

    async def async_step_quick_motion(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            self._triggers.append({
                "type": TRIGGER_MOTION,
                "entity_id": user_input["entity_id"],
                "title": user_input.get("title") or "Motion detected",
                "message": user_input.get("message") or "Motion was detected",
            })
            return await self.async_step_init()

        return self.async_show_form(
            step_id="quick_motion",
            data_schema=vol.Schema({
                vol.Required("entity_id"): EntitySelector(
                    EntitySelectorConfig(domain="binary_sensor", device_class="motion")
                ),
                vol.Optional("title", default="Motion detected"): TextSelector(),
                vol.Optional("message", default="Motion was detected"): TextSelector(),
            }),
        )

    async def async_step_quick_door(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            self._triggers.append({
                "type": TRIGGER_DOOR,
                "entity_id": user_input["entity_id"],
                "title": user_input.get("title") or "Door opened",
                "message": user_input.get("message") or "A door or window was opened",
            })
            return await self.async_step_init()

        return self.async_show_form(
            step_id="quick_door",
            data_schema=vol.Schema({
                vol.Required("entity_id"): EntitySelector(
                    EntitySelectorConfig(
                        domain="binary_sensor",
                        device_class=["door", "window", "garage_door", "opening"],
                    )
                ),
                vol.Optional("title", default="Door opened"): TextSelector(),
                vol.Optional("message", default="A door or window was opened"): TextSelector(),
            }),
        )

    async def async_step_quick_battery(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            self._triggers.append({
                "type": TRIGGER_BATTERY,
                "entity_id": user_input["entity_id"],
                "below": user_input.get("threshold", 20),
                "title": user_input.get("title") or "Battery low",
                "message": user_input.get("message") or "Battery is running low",
            })
            return await self.async_step_init()

        return self.async_show_form(
            step_id="quick_battery",
            data_schema=vol.Schema({
                vol.Required("entity_id"): EntitySelector(
                    EntitySelectorConfig(domain="sensor", device_class="battery")
                ),
                vol.Optional("threshold", default=20): NumberSelector(
                    NumberSelectorConfig(min=5, max=50, step=5, mode="slider", unit_of_measurement="%")
                ),
                vol.Optional("title", default="Battery low"): TextSelector(),
                vol.Optional("message", default="Battery is running low"): TextSelector(),
            }),
        )

    async def async_step_quick_unavailable(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            self._triggers.append({
                "type": TRIGGER_UNAVAILABLE,
                "entity_id": user_input["entity_id"],
                "title": user_input.get("title") or "Device unavailable",
                "message": user_input.get("message") or "A device became unavailable",
            })
            return await self.async_step_init()

        return self.async_show_form(
            step_id="quick_unavailable",
            data_schema=vol.Schema({
                vol.Required("entity_id"): EntitySelector(
                    EntitySelectorConfig()
                ),
                vol.Optional("title", default="Device unavailable"): TextSelector(),
                vol.Optional("message", default="A device became unavailable"): TextSelector(),
            }),
        )

    # ------------------------------------------------------------------
    # Advanced triggers
    # ------------------------------------------------------------------

    async def async_step_trigger_state(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            entity_id = user_input.get("entity_id", "")
            if not entity_id:
                errors["entity_id"] = "required"
            else:
                self._triggers.append({
                    "type": TRIGGER_STATE,
                    "entity_id": entity_id,
                    "to": user_input.get("to_state") or None,
                    "from": user_input.get("from_state") or None,
                    "title": user_input.get("title") or "State changed",
                    "message": user_input.get("message") or "State changed",
                })
                return await self.async_step_init()

        return self.async_show_form(
            step_id="trigger_state",
            errors=errors,
            data_schema=vol.Schema({
                vol.Required("entity_id"): EntitySelector(EntitySelectorConfig()),
                vol.Optional("to_state"): TextSelector(),
                vol.Optional("from_state"): TextSelector(),
                vol.Optional("title", default="State changed"): TextSelector(),
                vol.Optional("message", default="State changed"): TextSelector(),
            }),
        )

    async def async_step_trigger_numeric(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            entity_id = user_input.get("entity_id", "")
            if not entity_id:
                errors["entity_id"] = "required"
            elif user_input.get("above") is None and user_input.get("below") is None:
                errors["base"] = "above_or_below_required"
            else:
                self._triggers.append({
                    "type": TRIGGER_NUMERIC_STATE,
                    "entity_id": entity_id,
                    "above": user_input.get("above"),
                    "below": user_input.get("below"),
                    "title": user_input.get("title") or "Threshold reached",
                    "message": user_input.get("message") or "Value crossed threshold",
                })
                return await self.async_step_init()

        return self.async_show_form(
            step_id="trigger_numeric",
            errors=errors,
            data_schema=vol.Schema({
                vol.Required("entity_id"): EntitySelector(
                    EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("above"): NumberSelector(NumberSelectorConfig(mode="box")),
                vol.Optional("below"): NumberSelector(NumberSelectorConfig(mode="box")),
                vol.Optional("title", default="Threshold reached"): TextSelector(),
                vol.Optional("message", default="Value crossed threshold"): TextSelector(),
            }),
        )


def _describe_trigger(t: dict[str, Any]) -> str:
    t_type = t.get("type", "unknown")
    label = ALL_TRIGGER_TYPES.get(t_type, t_type)
    entity = t.get("entity_id", "")
    if t_type == TRIGGER_BATTERY:
        return f"{label}: {entity} below {t.get('below', 20)}%"
    if t_type == TRIGGER_NUMERIC_STATE:
        parts = []
        if t.get("above") is not None:
            parts.append(f"above {t['above']}")
        if t.get("below") is not None:
            parts.append(f"below {t['below']}")
        return f"{label}: {entity} {', '.join(parts)}"
    if t_type == TRIGGER_STATE:
        return f"{label}: {entity} -> {t.get('to') or 'any'}"
    return f"{label}: {entity}"