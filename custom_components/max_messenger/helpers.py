from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_ALLOWED_USERS,
    CONF_USERS,
    CONF_USER_ENABLED,
    CONF_USER_NAME,
    CONF_USER_PERMISSIONS,
    PERM_ALL,
    PERM_NOTIFICATIONS,
)

_LOGGER = logging.getLogger(__name__)

HOME_MENU_PAYLOAD = "home_main"
HOME_MENU_BUTTON = {
    "type": "callback",
    "text": "🏠 Управление домом",
    "payload": HOME_MENU_PAYLOAD,
}


def settings(entry: ConfigEntry) -> dict[str, Any]:
    return {**entry.data, **entry.options}


def with_home_menu_button(
    buttons: list[list[dict[str, Any]]] | None,
) -> list[list[dict[str, Any]]]:
    result: list[list[dict[str, Any]]] = []
    for row in buttons or []:
        if isinstance(row, list):
            result.append([dict(button) for button in row if isinstance(button, dict)])

    for row in result:
        if any(str(button.get("payload", "")) == HOME_MENU_PAYLOAD for button in row):
            return result

    result.append([dict(HOME_MENU_BUTTON)])
    return result


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


def user_profiles(cfg: dict[str, Any]) -> dict[int, dict[str, Any]]:
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
                CONF_USER_PERMISSIONS: [str(item) for item in permissions],
            }

    for user_id in _legacy_allowed_users(str(cfg.get(CONF_ALLOWED_USERS, "") or "")):
        result.setdefault(
            user_id,
            {
                CONF_USER_NAME: "",
                CONF_USER_ENABLED: True,
                CONF_USER_PERMISSIONS: [PERM_ALL],
            },
        )

    return result


def access_for_user(
    profiles: dict[int, dict[str, Any]],
    user_id: Any,
) -> tuple[bool, dict[str, Any] | None]:
    if not profiles:
        return True, None
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return False, None
    profile = profiles.get(uid)
    if profile is None:
        return False, None
    return bool(profile.get(CONF_USER_ENABLED, True)), profile


def notification_recipients(
    profiles: dict[int, dict[str, Any]],
    explicit_user_ids: list[int] | None = None,
    required_permission: str | None = None,
) -> list[int]:
    explicit = set(explicit_user_ids or [])
    result: list[int] = []

    for user_id, profile in profiles.items():
        if not profile.get(CONF_USER_ENABLED, True):
            continue
        if explicit and user_id not in explicit:
            continue

        permissions = set(profile.get(CONF_USER_PERMISSIONS, []))
        if PERM_ALL not in permissions and PERM_NOTIFICATIONS not in permissions:
            continue
        if required_permission and PERM_ALL not in permissions and required_permission not in permissions:
            continue
        result.append(user_id)

    return sorted(result)
