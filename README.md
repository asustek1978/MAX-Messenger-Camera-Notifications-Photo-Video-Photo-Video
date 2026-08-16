# Slava MAX for Home Assistant

Custom Home Assistant integration for **MAX Messenger** with notifications,
camera photo/video delivery, multiple users, ACL permissions and callbacks.

> Current public release: **0.5.5**

## English

### Features

- Home Assistant → MAX text notifications
- photo upload and delivery
- video upload and delivery
- camera blueprint with **Photo + video / Photo only / Video only**
- configurable automation triggers and conditions
- multiple MAX users
- per-user permissions configured from the Home Assistant UI
- `/start` and callback handling through long polling
- callback events for optional custom bot controls
- services for direct delivery and ACL-aware broadcast
- background polling that does not block Home Assistant startup

### Installation with HACS

This repository can be added as a **Custom repository** in HACS:

1. Open HACS.
2. Open the menu and choose **Custom repositories**.
3. Add this repository as category **Integration**.
4. Install **Slava MAX**.
5. Restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration → Slava MAX**.
7. Enter your MAX bot token in the Home Assistant UI.

The bot token is not stored in YAML and should never be committed to GitHub.

### Manual installation

Copy:

```text
custom_components/slava_max
```

to:

```text
/config/custom_components/slava_max
```

Restart Home Assistant and add **Slava MAX** from **Settings → Devices & services**.

### Camera blueprint

Blueprint file:

```text
blueprints/automation/slava_max/camera_snapshot_max.yaml
```

It can send:

- photo + video;
- photo only;
- video only.

The trigger is not hard-coded. You can use a motion sensor, camera person
detection, a doorbell, a door contact, or any other Home Assistant trigger.

For video, the selected camera must support `camera.record`.

Default media paths are:

```text
/media/slava_max_camera_latest.jpg
/media/slava_max_camera_latest.mp4
```

### Services

```text
slava_max.send_message
slava_max.broadcast
slava_max.send_image
slava_max.broadcast_image
slava_max.send_video
slava_max.broadcast_video
slava_max.answer_callback
```

Broadcast services use the Slava MAX ACL. Leaving `user_ids` empty sends to
all enabled users that have the required permissions.

### Callbacks

The integration exposes MAX callback updates as Home Assistant events, so you
can build your own bot controls and menus. A complete smart-home menu/router
is installation-specific and is not part of this camera-notification project.

### Permissions

The integration supports per-user permissions such as:

- `notifications`
- `lights`
- `climate`
- `devices`
- `water`
- `vacuum`
- `braga`
- `braga_emergency`
- `status`
- `intercom`
- `intercom_open`
- `cameras`
- `scenes`

### Security

- keep the MAX bot token private;
- unknown MAX users do not automatically receive smart-home access;
- permissions are checked before ACL broadcasts/control commands;
- sensitive actions can use separate permissions.

---

## Русский

### Возможности

- уведомления Home Assistant → MAX;
- отправка фотографий;
- отправка видео;
- blueprint камеры с режимами **Фото + видео / Фото / Видео**;
- произвольные триггеры и условия Home Assistant;
- несколько пользователей MAX;
- индивидуальные права пользователей через UI Home Assistant;
- `/start` и callback-события через Long Polling;
- события callback для собственных кнопок и меню бота;
- прямая отправка и рассылка с проверкой ACL;
- фоновый polling, который не задерживает запуск Home Assistant.

### Установка через HACS

Добавьте этот репозиторий в HACS как **Custom repository** категории
**Integration**, установите **Slava MAX**, перезапустите Home Assistant и
добавьте интеграцию через:

**Настройки → Устройства и службы → Добавить интеграцию → Slava MAX**

Токен MAX-бота вводится только через UI Home Assistant. Не храните его в
YAML и не публикуйте в GitHub.

### Ручная установка

Скопируйте:

```text
custom_components/slava_max
```

в:

```text
/config/custom_components/slava_max
```

и полностью перезапустите Home Assistant.

### Blueprint камеры

Файл:

```text
blueprints/automation/slava_max/camera_snapshot_max.yaml
```

Поддерживаются режимы:

- Фото + видео;
- Фото;
- Видео.

Триггер не привязан к конкретной камере или датчику. Можно выбрать движение,
обнаружение человека, домофон, открытие двери или любой другой триггер.

Для видео камера должна поддерживать `camera.record`.

### Получатели

Поле `MAX recipients / Получатели MAX` можно оставить пустым. Тогда рассылка
идёт всем включённым пользователям, у которых есть `notifications` и
дополнительное право, например `cameras`.

Несколько `user_id` указываются через запятую:

```text
123456789, 987654321
```

### Callback и собственное меню

Интеграция передаёт callback MAX в события Home Assistant. На их основе можно
сделать собственное меню управления. Готовый роутер конкретного умного дома в
этот публичный проект камеры не входит.

## Repository structure

```text
custom_components/slava_max/     Home Assistant integration
blueprints/automation/slava_max/ Camera automation blueprint
docs/community_post.md           Ready-to-use Home Assistant Community post
examples/                         Example automations
```

## Disclaimer

This is a community project and is not an official Home Assistant or MAX
integration.

## License

MIT License.
