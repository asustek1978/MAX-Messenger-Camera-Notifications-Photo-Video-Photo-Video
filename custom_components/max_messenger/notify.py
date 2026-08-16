from __future__ import annotations

from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import MaxMessengerApi
from .const import CONF_TARGET_ID, CONF_TARGET_TYPE, DOMAIN
from .helpers import notification_recipients, settings, user_profiles, with_home_menu_button


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN]["entries"][entry.entry_id]
    async_add_entities([MaxMessengerNotifyEntity(entry, runtime["api"])])


class MaxMessengerNotifyEntity(NotifyEntity):
    _attr_has_entity_name = True
    _attr_name = "Уведомления"
    _attr_icon = "mdi:message-badge-outline"

    def __init__(self, entry: ConfigEntry, api: MaxMessengerApi) -> None:
        self._entry = entry
        self._api = api
        stable_id = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{stable_id}_notify"

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        cfg = settings(self._entry)
        text = f"**{title}**\n\n{message}" if title else message
        profiles = user_profiles(cfg)
        recipients = notification_recipients(profiles)

        if profiles:
            for user_id in recipients:
                await self._api.send_message(
                    text=text,
                    target_type="user_id",
                    target_id=user_id,
                    fmt="markdown",
                    notify=True,
                    buttons=with_home_menu_button(None),
                )
        else:
            await self._api.send_message(
                text=text,
                target_type=cfg[CONF_TARGET_TYPE],
                target_id=int(cfg[CONF_TARGET_ID]),
                fmt="markdown",
                notify=True,
                buttons=with_home_menu_button(None),
            )

        self._async_record_notification()
