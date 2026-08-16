from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MaxMessengerApi
from .const import CONF_POLLING, CONF_TOKEN, DOMAIN
from .helpers import settings
from .polling import poll_loop
from .services import register_services

PLATFORMS = [Platform.NOTIFY]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("entries", {})
    await register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MAX Messenger Notifications without blocking Home Assistant startup."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("entries", {})
    await register_services(hass)

    api = MaxMessengerApi(async_get_clientsession(hass), entry.data[CONF_TOKEN])
    runtime: dict[str, Any] = {
        "entry": entry,
        "api": api,
        "poll_task": None,
        "pending_users": {},
    }
    hass.data[DOMAIN]["entries"][entry.entry_id] = runtime

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if settings(entry).get(CONF_POLLING, True):
        runtime["poll_task"] = hass.async_create_background_task(
            poll_loop(hass, entry, api),
            f"max_messenger_poll_{entry.entry_id}",
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    runtime = hass.data.get(DOMAIN, {}).get("entries", {}).pop(entry.entry_id, None)
    if runtime and runtime.get("poll_task"):
        task = runtime["poll_task"]
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    return True
