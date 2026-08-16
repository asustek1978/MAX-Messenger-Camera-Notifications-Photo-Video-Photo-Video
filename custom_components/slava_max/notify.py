from __future__ import annotations

from typing import Any

from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import SlavaMaxApi
from .const import (
    CONF_TARGET_ID,
    CONF_TARGET_TYPE,
    DOMAIN,
)
from . import (
    _notification_recipients,
    _user_profiles,
    _with_home_menu_button,
    settings,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN]["entries"][entry.entry_id]
    async_add_entities(
        [SlavaMaxNotifyEntity(entry, runtime["api"])]
    )


class SlavaMaxNotifyEntity(NotifyEntity):
    _attr_has_entity_name = True
    _attr_name = "Уведомления"
    _attr_icon = "mdi:message-badge-outline"

    def __init__(
        self,
        entry: ConfigEntry,
        api: SlavaMaxApi,
    ) -> None:
        self._entry = entry
        self._api = api
        stable_id = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{stable_id}_notify"

    async def async_send_message(
        self,
        message: str,
        title: str | None = None,
    ) -> None:
        cfg = settings(self._entry)

        text = message
        if title:
            text = f"**{title}**\n\n{message}"

        profiles = _user_profiles(cfg)
        recipients = _notification_recipients(profiles)

        if profiles:
            for user_id in recipients:
                await self._api.send_message(
                    text=text,
                    target_type="user_id",
                    target_id=user_id,
                    fmt="markdown",
                    notify=True,
                    buttons=_with_home_menu_button(None),
                )
        else:
            await self._api.send_message(
                text=text,
                target_type=cfg[CONF_TARGET_TYPE],
                target_id=int(cfg[CONF_TARGET_ID]),
                fmt="markdown",
                notify=True,
                buttons=_with_home_menu_button(None),
            )

        self._async_record_notification()
