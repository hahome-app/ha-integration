"""HAHome integration — relays notifications via HA mobile_app."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_DEVICE_NAME,
    CONF_TRIGGERS,
    CONF_WEBHOOK_ID,
    DOMAIN,
    TRIGGER_BATTERY,
    TRIGGER_DOOR,
    TRIGGER_MOTION,
    TRIGGER_NUMERIC_STATE,
    TRIGGER_STATE,
    TRIGGER_UNAVAILABLE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HAHome from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    triggers: list[dict[str, Any]] = entry.options.get(CONF_TRIGGERS, [])
    manager = HAHomeTriggerManager(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = manager

    await manager.async_setup_triggers(triggers)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    manager: HAHomeTriggerManager = hass.data[DOMAIN].pop(entry.entry_id)
    manager.async_unload()
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _slugify(name: str) -> str:
    """Match HA's slugification: lowercase, replace non-alphanumeric with underscore."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


class HAHomeTriggerManager:
    """Manages trigger subscriptions and fires notifications via mobile_app."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._unsubs: list[Any] = []

    async def async_setup_triggers(self, triggers: list[dict[str, Any]]) -> None:
        _LOGGER.debug("HAHome: setting up %d triggers", len(triggers))
        for trigger in triggers:
            t_type = trigger.get("type")
            if t_type == TRIGGER_MOTION:
                self._setup_binary_on_trigger(trigger)
            elif t_type == TRIGGER_DOOR:
                self._setup_binary_on_trigger(trigger)
            elif t_type == TRIGGER_UNAVAILABLE:
                self._setup_unavailable_trigger(trigger)
            elif t_type == TRIGGER_BATTERY:
                self._setup_battery_trigger(trigger)
            elif t_type == TRIGGER_STATE:
                self._setup_state_trigger(trigger)
            elif t_type == TRIGGER_NUMERIC_STATE:
                self._setup_numeric_trigger(trigger)
            else:
                _LOGGER.warning("HAHome: unknown trigger type '%s'", t_type)

    def _setup_binary_on_trigger(self, trigger: dict[str, Any]) -> None:
        """Fire when a binary sensor turns on."""
        entity_id: str = trigger["entity_id"]
        title: str = trigger.get("title", "HAHome")
        message: str = trigger.get("message", "")

        @callback
        def _state_changed(event):
            new_state = event.data.get("new_state")
            if new_state and new_state.state == "on":
                self._send_notification(title, message, {"entity_id": entity_id})

        self._unsubs.append(
            async_track_state_change_event(self.hass, [entity_id], _state_changed)
        )

    def _setup_unavailable_trigger(self, trigger: dict[str, Any]) -> None:
        """Fire when an entity becomes unavailable."""
        entity_id: str = trigger["entity_id"]
        title: str = trigger.get("title", "Device unavailable")
        message: str = trigger.get("message", f"{entity_id} is unavailable")

        @callback
        def _state_changed(event):
            new_state = event.data.get("new_state")
            if new_state and new_state.state == "unavailable":
                self._send_notification(title, message, {"entity_id": entity_id})

        self._unsubs.append(
            async_track_state_change_event(self.hass, [entity_id], _state_changed)
        )

    def _setup_battery_trigger(self, trigger: dict[str, Any]) -> None:
        """Fire when battery drops below threshold (crossing only)."""
        entity_id: str = trigger["entity_id"]
        below: float = float(trigger.get("below", 20))
        title: str = trigger.get("title", "Battery low")
        message: str = trigger.get("message", f"{entity_id} battery is low")

        @callback
        def _state_changed(event):
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")
            if not new_state:
                return
            try:
                new_val = float(new_state.state)
                old_val = float(old_state.state) if old_state else 100.0
                if new_val < below <= old_val:
                    self._send_notification(title, message, {"entity_id": entity_id})
            except (ValueError, TypeError):
                pass

        self._unsubs.append(
            async_track_state_change_event(self.hass, [entity_id], _state_changed)
        )

    def _setup_state_trigger(self, trigger: dict[str, Any]) -> None:
        """Fire on state change with optional from/to filter."""
        entity_id: str = trigger["entity_id"]
        to_state: str | None = trigger.get("to")
        from_state: str | None = trigger.get("from")
        title: str = trigger.get("title", "HAHome")
        message: str = trigger.get("message", "State changed")

        @callback
        def _state_changed(event):
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")
            if to_state and (not new_state or new_state.state != to_state):
                return
            if from_state and (not old_state or old_state.state != from_state):
                return
            self._send_notification(title, message, {"entity_id": entity_id})

        self._unsubs.append(
            async_track_state_change_event(self.hass, [entity_id], _state_changed)
        )

    def _setup_numeric_trigger(self, trigger: dict[str, Any]) -> None:
        """Fire when a numeric sensor crosses above/below a threshold."""
        entity_id: str = trigger["entity_id"]
        above: float | None = trigger.get("above")
        below: float | None = trigger.get("below")
        title: str = trigger.get("title", "HAHome")
        message: str = trigger.get("message", "Threshold crossed")

        @callback
        def _state_changed(event):
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")
            if not new_state:
                return
            try:
                new_val = float(new_state.state)
                old_val = float(old_state.state) if old_state else None
                crossed = False
                if above is not None and old_val is not None:
                    crossed = crossed or (new_val > above and old_val <= above)
                if below is not None and old_val is not None:
                    crossed = crossed or (new_val < below and old_val >= below)
                if crossed:
                    self._send_notification(
                        title, f"{message} ({new_val})", {"entity_id": entity_id}
                    )
            except (ValueError, TypeError):
                pass

        self._unsubs.append(
            async_track_state_change_event(self.hass, [entity_id], _state_changed)
        )

    @callback
    def _send_notification(
        self, title: str, message: str, data: dict[str, Any]
    ) -> None:
        """Send push notification via mobile_app notify service."""
        device_name = self.entry.data.get(CONF_DEVICE_NAME, "")
        slug = _slugify(device_name)
        service = f"mobile_app_{slug}"

        _LOGGER.debug("HAHome: sending '%s' via notify.%s", title, service)

        self.hass.async_create_task(
            self.hass.services.async_call(
                "notify",
                service,
                {
                    "title": title,
                    "message": message,
                    "data": {
                        "push": {"sound": "default"},
                        **data,
                    },
                },
            )
        )

    @callback
    def async_unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()