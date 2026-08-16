from __future__ import annotations

import asyncio
import logging
import mimetypes
from contextlib import suppress
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SlavaMaxApi, SlavaMaxApiError
from .const import (
    CONF_ALLOWED_USERS,
    CONF_POLLING,
    CONF_TARGET_ID,
    CONF_TARGET_TYPE,
    CONF_TOKEN,
    CONF_USERS,
    CONF_USER_ENABLED,
    CONF_USER_NAME,
    CONF_USER_PERMISSIONS,
    DOMAIN,
    EVENT_ACCESS_REQUEST,
    EVENT_NAME,
    PERM_ALL,
    PERM_NOTIFICATIONS,
    SERVICE_ANSWER_CALLBACK,
    SERVICE_BROADCAST,
    SERVICE_BROADCAST_IMAGE,
    SERVICE_BROADCAST_VIDEO,
    SERVICE_SEND_IMAGE,
    SERVICE_SEND_MESSAGE,
    SERVICE_SEND_VIDEO,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.NOTIFY]

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_TEXT = "message"
ATTR_FILE_PATH = "file_path"
ATTR_CHAT_ID = "chat_id"
ATTR_USER_ID = "user_id"
ATTR_USER_IDS = "user_ids"
ATTR_REQUIRED_PERMISSION = "required_permission"
ATTR_FORMAT = "format"
ATTR_NOTIFY = "notify"
ATTR_BUTTONS = "buttons"
ATTR_DISABLE_LINK_PREVIEW = "disable_link_preview"
ATTR_CALLBACK_ID = "callback_id"

HOME_MENU_PAYLOAD = "home_main"
HOME_MENU_BUTTON = {
    "type": "callback",
    "text": "🏠 Управление домом",
    "payload": HOME_MENU_PAYLOAD,
}


def settings(entry: ConfigEntry) -> dict[str, Any]:
    """Return config-entry data merged with options."""
    return {**entry.data, **entry.options}


def _legacy_allowed_users(value: str) -> set[int]:
    result: set[int] = set()
    for item in (value or "").replace(";", ",").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            result.add(int(item))
        except ValueError:
            _LOGGER.warning("Ignored invalid allowed MAX user id: %s", item)
    return result


def _user_profiles(cfg: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Build ACL profiles with legacy allowed_users compatibility."""
    result: dict[int, dict[str, Any]] = {}
    raw_users = cfg.get(CONF_USERS, {})

    if isinstance(raw_users, dict):
        for raw_id, raw_profile in raw_users.items():
            try:
                user_id = int(raw_id)
            except (TypeError, ValueError):
                continue

            profile = raw_profile if isinstance(raw_profile, dict) else {}
            permissions = profile.get(CONF_USER_PERMISSIONS, [])
            if not isinstance(permissions, list):
                permissions = []

            result[user_id] = {
                CONF_USER_NAME: str(profile.get(CONF_USER_NAME, "")).strip(),
                CONF_USER_ENABLED: bool(profile.get(CONF_USER_ENABLED, True)),
                CONF_USER_PERMISSIONS: list(permissions),
            }

    for user_id in _legacy_allowed_users(str(cfg.get(CONF_ALLOWED_USERS, ""))):
        result.setdefault(
            user_id,
            {
                CONF_USER_NAME: "",
                CONF_USER_ENABLED: True,
                CONF_USER_PERMISSIONS: [PERM_ALL],
            },
        )

    return result


def _has_permission(profile: dict[str, Any], permission: str | None) -> bool:
    if not profile.get(CONF_USER_ENABLED, True):
        return False
    permissions = profile.get(CONF_USER_PERMISSIONS, [])
    if not isinstance(permissions, list):
        return False
    if PERM_ALL in permissions:
        return True
    if not permission:
        return True
    return permission in permissions


def _notification_recipients(
    profiles: dict[int, dict[str, Any]],
    user_ids: list[int] | None = None,
    required_permission: str | None = None,
) -> list[int]:
    selected = set(user_ids or [])
    recipients: list[int] = []

    for user_id, profile in profiles.items():
        if selected and user_id not in selected:
            continue
        if not _has_permission(profile, PERM_NOTIFICATIONS):
            continue
        if required_permission and not _has_permission(profile, required_permission):
            continue
        recipients.append(user_id)

    return recipients


def _with_home_menu_button(
    buttons: list[list[dict[str, Any]]] | None,
) -> list[list[dict[str, Any]]]:
    """Append a reusable Home button to notification messages."""
    result: list[list[dict[str, Any]]] = []
    for row in buttons or []:
        if isinstance(row, list):
            result.append([dict(item) for item in row if isinstance(item, dict)])

    for row in result:
        if any(str(item.get("payload", "")) == HOME_MENU_PAYLOAD for item in row):
            return result

    result.append([dict(HOME_MENU_BUTTON)])
    return result


def _validate_user_ids(value: Any) -> list[int]:
    """Normalize recipient IDs accepted by services and blueprints."""
    if value in (None, "", {}, []):
        return []
    if isinstance(value, (list, tuple, set)):
        return [int(item) for item in value if str(item).strip()]
    if isinstance(value, dict):
        raise vol.Invalid("user_ids must be a list of MAX user IDs")
    try:
        return [int(value)]
    except (TypeError, ValueError) as err:
        raise vol.Invalid("user_ids must be a list of MAX user IDs") from err


COMMON_SEND = {
    vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    vol.Optional(ATTR_FORMAT, default="markdown"): vol.In(["markdown", "html", "plain"]),
    vol.Optional(ATTR_NOTIFY, default=True): cv.boolean,
    vol.Optional(ATTR_BUTTONS): list,
    vol.Optional(ATTR_DISABLE_LINK_PREVIEW, default=False): cv.boolean,
}

SEND_SCHEMA = vol.Schema({
    **COMMON_SEND,
    vol.Required(ATTR_TEXT): cv.string,
    vol.Optional(ATTR_CHAT_ID): vol.Coerce(int),
    vol.Optional(ATTR_USER_ID): vol.Coerce(int),
})

BROADCAST_SCHEMA = vol.Schema({
    **COMMON_SEND,
    vol.Required(ATTR_TEXT): cv.string,
    vol.Optional(ATTR_USER_IDS): _validate_user_ids,
    vol.Optional(ATTR_REQUIRED_PERMISSION): cv.string,
})

SEND_MEDIA_SCHEMA = vol.Schema({
    **COMMON_SEND,
    vol.Required(ATTR_FILE_PATH): cv.string,
    vol.Optional(ATTR_TEXT, default=""): cv.string,
    vol.Optional(ATTR_CHAT_ID): vol.Coerce(int),
    vol.Optional(ATTR_USER_ID): vol.Coerce(int),
})

BROADCAST_MEDIA_SCHEMA = vol.Schema({
    **COMMON_SEND,
    vol.Required(ATTR_FILE_PATH): cv.string,
    vol.Optional(ATTR_TEXT, default=""): cv.string,
    vol.Optional(ATTR_USER_IDS): _validate_user_ids,
    vol.Optional(ATTR_REQUIRED_PERMISSION): cv.string,
})

ANSWER_SCHEMA = vol.Schema({
    vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    vol.Required(ATTR_CALLBACK_ID): cv.string,
    vol.Optional(ATTR_TEXT): cv.string,
    vol.Optional(ATTR_FORMAT, default="markdown"): vol.In(["markdown", "html", "plain"]),
    vol.Optional(ATTR_BUTTONS): list,
})


def _entry_runtime(hass: HomeAssistant, entry_id: str | None = None) -> dict[str, Any]:
    entries = hass.data.get(DOMAIN, {}).get("entries", {})
    if entry_id:
        runtime = entries.get(entry_id)
        if runtime:
            return runtime
        raise HomeAssistantError(f"Slava MAX config entry not found: {entry_id}")
    if len(entries) == 1:
        return next(iter(entries.values()))
    if not entries:
        raise HomeAssistantError("Slava MAX is not configured")
    raise HomeAssistantError("Multiple Slava MAX entries exist; specify config_entry_id")


def _target(call: ServiceCall, cfg: dict[str, Any]) -> tuple[str, int]:
    if ATTR_USER_ID in call.data:
        return "user_id", int(call.data[ATTR_USER_ID])
    if ATTR_CHAT_ID in call.data:
        return "chat_id", int(call.data[ATTR_CHAT_ID])
    return str(cfg[CONF_TARGET_TYPE]), int(cfg[CONF_TARGET_ID])


def _fmt(call: ServiceCall) -> str | None:
    value = call.data.get(ATTR_FORMAT, "markdown")
    return None if value == "plain" else str(value)


async def _read_media(path_value: str) -> tuple[bytes, str, str]:
    path = Path(path_value)
    try:
        data = await asyncio.to_thread(path.read_bytes)
    except OSError as err:
        raise HomeAssistantError(f"Cannot read media file {path}: {err}") from err
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return data, path.name, content_type


async def _broadcast_targets(
    runtime: dict[str, Any],
    user_ids: list[int],
    required_permission: str | None,
) -> list[int]:
    cfg = settings(runtime["entry"])
    profiles = _user_profiles(cfg)
    if not profiles:
        if cfg.get(CONF_TARGET_TYPE) == "user_id":
            return [int(cfg[CONF_TARGET_ID])]
        return []
    return _notification_recipients(profiles, user_ids, required_permission)


def _register_services(hass: HomeAssistant) -> None:
    async def send_message(call: ServiceCall) -> None:
        runtime = _entry_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        cfg = settings(runtime["entry"])
        target_type, target_id = _target(call, cfg)
        await runtime["api"].send_message(
            text=call.data[ATTR_TEXT], target_type=target_type, target_id=target_id,
            fmt=_fmt(call), notify=call.data[ATTR_NOTIFY],
            buttons=call.data.get(ATTR_BUTTONS),
            disable_link_preview=call.data[ATTR_DISABLE_LINK_PREVIEW],
        )

    async def broadcast(call: ServiceCall) -> None:
        runtime = _entry_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        recipients = await _broadcast_targets(runtime, call.data.get(ATTR_USER_IDS, []), call.data.get(ATTR_REQUIRED_PERMISSION))
        for user_id in recipients:
            await runtime["api"].send_message(
                text=call.data[ATTR_TEXT], target_type="user_id", target_id=user_id,
                fmt=_fmt(call), notify=call.data[ATTR_NOTIFY],
                buttons=_with_home_menu_button(call.data.get(ATTR_BUTTONS)),
                disable_link_preview=call.data[ATTR_DISABLE_LINK_PREVIEW],
            )

    async def send_image(call: ServiceCall) -> None:
        runtime = _entry_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        cfg = settings(runtime["entry"])
        target_type, target_id = _target(call, cfg)
        data, filename, content_type = await _read_media(call.data[ATTR_FILE_PATH])
        token = await runtime["api"].upload_image(data=data, filename=filename, content_type=content_type)
        await runtime["api"].send_image_token(
            token=token, text=call.data[ATTR_TEXT], target_type=target_type, target_id=target_id,
            fmt=_fmt(call), notify=call.data[ATTR_NOTIFY], buttons=call.data.get(ATTR_BUTTONS),
            disable_link_preview=call.data[ATTR_DISABLE_LINK_PREVIEW],
        )

    async def broadcast_image(call: ServiceCall) -> None:
        runtime = _entry_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        data, filename, content_type = await _read_media(call.data[ATTR_FILE_PATH])
        token = await runtime["api"].upload_image(data=data, filename=filename, content_type=content_type)
        recipients = await _broadcast_targets(runtime, call.data.get(ATTR_USER_IDS, []), call.data.get(ATTR_REQUIRED_PERMISSION))
        for user_id in recipients:
            await runtime["api"].send_image_token(
                token=token, text=call.data[ATTR_TEXT], target_type="user_id", target_id=user_id,
                fmt=_fmt(call), notify=call.data[ATTR_NOTIFY],
                buttons=_with_home_menu_button(call.data.get(ATTR_BUTTONS)),
                disable_link_preview=call.data[ATTR_DISABLE_LINK_PREVIEW],
            )

    async def send_video(call: ServiceCall) -> None:
        runtime = _entry_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        cfg = settings(runtime["entry"])
        target_type, target_id = _target(call, cfg)
        data, filename, content_type = await _read_media(call.data[ATTR_FILE_PATH])
        token = await runtime["api"].upload_video(data=data, filename=filename, content_type=content_type)
        await runtime["api"].send_video_token(
            token=token, text=call.data[ATTR_TEXT], target_type=target_type, target_id=target_id,
            fmt=_fmt(call), notify=call.data[ATTR_NOTIFY], buttons=call.data.get(ATTR_BUTTONS),
            disable_link_preview=call.data[ATTR_DISABLE_LINK_PREVIEW],
        )

    async def broadcast_video(call: ServiceCall) -> None:
        runtime = _entry_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        data, filename, content_type = await _read_media(call.data[ATTR_FILE_PATH])
        token = await runtime["api"].upload_video(data=data, filename=filename, content_type=content_type)
        recipients = await _broadcast_targets(runtime, call.data.get(ATTR_USER_IDS, []), call.data.get(ATTR_REQUIRED_PERMISSION))
        for user_id in recipients:
            await runtime["api"].send_video_token(
                token=token, text=call.data[ATTR_TEXT], target_type="user_id", target_id=user_id,
                fmt=_fmt(call), notify=call.data[ATTR_NOTIFY],
                buttons=_with_home_menu_button(call.data.get(ATTR_BUTTONS)),
                disable_link_preview=call.data[ATTR_DISABLE_LINK_PREVIEW],
            )

    async def answer_callback(call: ServiceCall) -> None:
        runtime = _entry_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        await runtime["api"].answer_callback(
            callback_id=call.data[ATTR_CALLBACK_ID], text=call.data.get(ATTR_TEXT),
            fmt=_fmt(call), buttons=call.data.get(ATTR_BUTTONS),
        )

    handlers = {
        SERVICE_SEND_MESSAGE: (send_message, SEND_SCHEMA),
        SERVICE_BROADCAST: (broadcast, BROADCAST_SCHEMA),
        SERVICE_SEND_IMAGE: (send_image, SEND_MEDIA_SCHEMA),
        SERVICE_BROADCAST_IMAGE: (broadcast_image, BROADCAST_MEDIA_SCHEMA),
        SERVICE_SEND_VIDEO: (send_video, SEND_MEDIA_SCHEMA),
        SERVICE_BROADCAST_VIDEO: (broadcast_video, BROADCAST_MEDIA_SCHEMA),
        SERVICE_ANSWER_CALLBACK: (answer_callback, ANSWER_SCHEMA),
    }
    for service, (handler, schema) in handlers.items():
        if not hass.services.has_service(DOMAIN, service):
            hass.services.async_register(DOMAIN, service, handler, schema=schema)


def _extract_sender(update: dict[str, Any]) -> tuple[int | None, dict[str, Any]]:
    message = update.get("message") if isinstance(update.get("message"), dict) else {}
    sender = message.get("sender") if isinstance(message.get("sender"), dict) else {}
    if not sender and isinstance(update.get("user"), dict):
        sender = update["user"]
    raw_id = sender.get("user_id") or sender.get("id")
    try:
        return int(raw_id), sender
    except (TypeError, ValueError):
        return None, sender


async def _poll_loop(hass: HomeAssistant, entry: ConfigEntry, api: SlavaMaxApi) -> None:
    marker: int | None = None
    runtime = hass.data[DOMAIN]["entries"][entry.entry_id]
    while True:
        try:
            payload = await api.get_updates(marker=marker, timeout=30)
            updates = payload.get("updates", [])
            new_marker = payload.get("marker")
            if new_marker is not None:
                with suppress(TypeError, ValueError):
                    marker = int(new_marker)
            for update in updates if isinstance(updates, list) else []:
                if not isinstance(update, dict):
                    continue
                user_id, sender = _extract_sender(update)
                if user_id is not None:
                    runtime.setdefault("pending_users", {})[str(user_id)] = {
                        "name": " ".join(str(sender.get(key, "")).strip() for key in ("first_name", "last_name") if str(sender.get(key, "")).strip()),
                        "username": str(sender.get("username", "")).strip(),
                    }
                event_data = dict(update)
                if user_id is not None:
                    event_data["user_id"] = user_id
                event_data["config_entry_id"] = entry.entry_id
                hass.bus.async_fire(EVENT_NAME, event_data)
                cfg = settings(entry)
                profiles = _user_profiles(cfg)
                if user_id is not None and profiles and user_id not in profiles:
                    hass.bus.async_fire(EVENT_ACCESS_REQUEST, {"config_entry_id": entry.entry_id, "user_id": user_id, "sender": sender})
        except asyncio.CancelledError:
            raise
        except SlavaMaxApiError as err:
            _LOGGER.warning("MAX polling error: %s", err)
            await asyncio.sleep(5)
        except Exception:
            _LOGGER.exception("Unexpected MAX polling error")
            await asyncio.sleep(5)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    hass.data.setdefault(DOMAIN, {}).setdefault("entries", {})
    _register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {}).setdefault("entries", {})
    _register_services(hass)
    api = SlavaMaxApi(async_get_clientsession(hass), entry.data[CONF_TOKEN])
    runtime: dict[str, Any] = {"entry": entry, "api": api, "pending_users": {}, "poll_task": None}
    hass.data[DOMAIN]["entries"][entry.entry_id] = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if settings(entry).get(CONF_POLLING, True):
        runtime["poll_task"] = hass.async_create_background_task(
            _poll_loop(hass, entry, api), f"slava_max_poll_{entry.entry_id}"
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    runtime = hass.data.get(DOMAIN, {}).get("entries", {}).pop(entry.entry_id, None)
    if runtime and runtime.get("poll_task"):
        runtime["poll_task"].cancel()
        with suppress(asyncio.CancelledError):
            await runtime["poll_task"]
    return unload_ok
