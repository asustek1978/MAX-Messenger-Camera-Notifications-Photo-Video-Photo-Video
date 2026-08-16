# MAX Messenger Notifications for Home Assistant

Unofficial Home Assistant custom integration for the **MAX Messenger Bot API**.

It adds MAX messaging to Home Assistant, including text, images, video, inline buttons, multiple users, and ACL-based permissions. The repository also includes a reusable camera blueprint that can send **photo**, **video**, or **photo + video** when any Home Assistant trigger fires.

> This project is community-made and is not affiliated with Home Assistant or MAX.

## Features

- Multiple MAX users
- Per-user permissions / ACL
- Text messages and broadcasts
- Image upload and delivery
- Video upload and delivery
- Inline callback buttons
- Optional `🏠 Управление домом` / Smart Home button on notifications
- Camera automation blueprint:
  - Photo only
  - Video only
  - Photo + video
  - Custom triggers and conditions
  - Configurable video duration
  - Recipient filtering by permission
- Non-blocking long polling so the integration does not hold Home Assistant startup

## Requirements

- Home Assistant with custom integrations enabled
- A MAX bot token
- Network access from Home Assistant to the MAX Bot API
- For snapshot notifications: a working `camera` entity
- For video notifications: the camera must support `camera.record`
- A writable media path. `/media` is recommended for the included blueprint.

## Installation

### Manual installation

Copy:

```text
custom_components/max_messenger/
```

to:

```text
/config/custom_components/max_messenger/
```

Restart Home Assistant, then add **MAX Messenger Notifications** from:

**Settings → Devices & services → Add integration**

### HACS custom repository

This public repository can be added to HACS as a custom **Integration** repository. Install **MAX Messenger Notifications** and restart Home Assistant.

## Services / actions

The integration provides:

```text
max_messenger.send_message
max_messenger.broadcast
max_messenger.send_image
max_messenger.broadcast_image
max_messenger.send_video
max_messenger.broadcast_video
max_messenger.answer_callback
```

Example image broadcast:

```yaml
action: max_messenger.broadcast_image
data:
  file_path: /media/camera_latest.jpg
  message: "📷 Camera event"
  required_permission: cameras
  format: markdown
  notify: true
```

Example video broadcast:

```yaml
action: max_messenger.broadcast_video
data:
  file_path: /media/camera_latest.mp4
  message: "🎥 Camera event"
  required_permission: cameras
  format: markdown
  notify: true
```

## Camera blueprint

Blueprint file:

```text
blueprints/automation/max_messenger/camera_notifications.yaml
```

It accepts arbitrary Home Assistant triggers and conditions. No personal entity IDs are hard-coded.

The blueprint supports:

- **Photo + video**
- **Photo only**
- **Video only**
- configurable snapshot delay
- configurable video duration from 3 to 60 seconds
- explicit MAX user IDs or ACL-based broadcast
- additional actions before and after media delivery
- cooldown protection

### Import

Use this public blueprint URL:

```text
https://github.com/asustek1978/MAX-Messenger-Notifications/blob/main/blueprints/automation/max_messenger/camera_notifications.yaml
```

Then in Home Assistant:

**Settings → Automations & scenes → Blueprints → Import blueprint**

## ACL

Users configured in MAX Messenger Notifications can have different permissions. For camera notifications the included blueprint defaults to:

```text
cameras
```

A broadcast is sent only to enabled recipients that satisfy the configured permissions.

## Security

Never commit your MAX bot token, Home Assistant secrets, passwords, private URLs, or personal configuration to a public repository.

## Русский

### Что это

**MAX Messenger Notifications** — неофициальная пользовательская интеграция Home Assistant для ботов MAX.

Поддерживается:

- несколько пользователей;
- права доступа;
- текстовые сообщения;
- фото;
- видео;
- callback-кнопки;
- рассылки;
- кнопка `🏠 Управление домом`;
- blueprint камеры с выбором **Фото + видео / Фото / Видео**.

### Установка

Скопируйте:

```text
custom_components/max_messenger/
```

в:

```text
/config/custom_components/max_messenger/
```

Перезапустите Home Assistant и добавьте интеграцию **MAX Messenger Notifications** через **Настройки → Устройства и службы**.

Для blueprint видео камера должна поддерживать действие `camera.record`.

## License

MIT License. See [LICENSE](LICENSE).
