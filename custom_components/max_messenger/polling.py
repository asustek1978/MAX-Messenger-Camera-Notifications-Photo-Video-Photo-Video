from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import MaxMessengerApi, MaxMessengerApiError
from .const import (
    CONF_USER_NAME,
    CONF_USER_PERMISSIONS,
    DOMAIN,
    EVENT_ACCESS_REQUEST,
    EVENT_NAME,
    PERM_ALL,
)
from .helpers import access_for_user, settings, user_profiles

_LOGGER = logging.getLogger(__name__)


def event_data(update: dict[str, Any]) -> dict[str, Any]:
    update_type = update.get("update_type") or "unknown"
    callback = update.get("callback") or {}
    message = update.get("message") or callback.get("message") or {}
    user = (
        update.get("user")
        or callback.get("user")
        or message.get("sender")
        or message.get("user")
        or {}
    )
    body = message.get("body") or {}
    text = body.get("text") or message.get("text") or update.get("text") or ""

    command = None
    args = ""
    if isinstance(text, str) and text.startswith("/"):
        raw = text[1:].strip()
        if raw:
            parts = raw.split(maxsplit=1)
            command = parts[0].split("@", 1)[0].lower()
            if len(parts) > 1:
                args = parts[1]

    recipient = message.get("recipient") or {}
    return {
        "type": "callback" if update_type == "message_callback" else "message" if update_type == "message_created" else update_type,
        "update_type": update_type,
        "timestamp": update.get("timestamp"),
        "chat_id": update.get("chat_id") or message.get("chat_id") or recipient.get("chat_id"),
        "user_id": user.get("user_id") or user.get("id"),
        "username": user.get("username"),
        "name": user.get("first_name") or user.get("name"),
        "text": text,
        "command": command,
        "args": args,
        "callback_id": callback.get("callback_id"),
        "payload": callback.get("payload") or callback.get("data") or update.get("payload"),
        "message_id": message.get("message_id") or message.get("id") or callback.get("message_id"),
        "raw": update,
    }


async def poll_loop(
    hass: HomeAssistant,
    entry: ConfigEntry,
    api: MaxMessengerApi,
) -> None:
    marker: int | None = None
    initialized = False

    while True:
        try:
            profiles = user_profiles(settings(entry))
            result = await api.get_updates(marker, timeout=30)
            next_marker = result.get("marker")

            if not initialized:
                marker = next_marker
                initialized = True
                continue

            for update in result.get("updates", []):
                data = event_data(update)
                user_id = data.get("user_id")
                authorized, profile = access_for_user(profiles, user_id)

                if not authorized:
                    try:
                        pending_user_id = int(user_id)
                    except (TypeError, ValueError):
                        continue

                    runtime = hass.data.get(DOMAIN, {}).get("entries", {}).get(entry.entry_id)
                    if runtime is not None:
                        runtime.setdefault("pending_users", {})[str(pending_user_id)] = {
                            "user_id": pending_user_id,
                            "name": data.get("name") or "",
                            "username": data.get("username") or "",
                        }
                    hass.bus.async_fire(
                        EVENT_ACCESS_REQUEST,
                        {
                            "config_entry_id": entry.entry_id,
                            "user_id": pending_user_id,
                            "name": data.get("name") or "",
                            "username": data.get("username") or "",
                        },
                    )
                    continue

                permissions = (
                    list(profile.get(CONF_USER_PERMISSIONS, []))
                    if profile is not None
                    else [PERM_ALL]
                )
                data.update(
                    {
                        "config_entry_id": entry.entry_id,
                        "authorized": True,
                        "permissions": permissions,
                        "access_name": profile.get(CONF_USER_NAME, "") if profile else "",
                    }
                )
                hass.bus.async_fire(EVENT_NAME, data)

            if next_marker is not None:
                marker = next_marker

        except asyncio.CancelledError:
            raise
        except MaxMessengerApiError as err:
            _LOGGER.warning("MAX polling error: %s", err)
            await asyncio.sleep(10)
        except Exception:
            _LOGGER.exception("Unexpected MAX polling error")
            await asyncio.sleep(10)
