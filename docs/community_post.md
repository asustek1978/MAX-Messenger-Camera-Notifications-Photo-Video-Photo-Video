# MAX Messenger Notifications — Camera Photo / Video / Photo+Video

This Home Assistant blueprint sends camera events to **MAX Messenger** using the companion **MAX Messenger Notifications** custom integration.

## What it does

The automation can run from any Home Assistant trigger, for example camera motion, person detection, a doorbell, a door opening, or another automation trigger.

For each event you can choose **Photo + video**, **Photo only**, or **Video only**. The blueprint also supports conditions, configurable snapshot delay, configurable video duration, cooldown protection, additional actions, and ACL-based recipients.

## Requirements

1. Home Assistant
2. MAX Messenger Notifications custom integration v0.6.0+
3. MAX bot token
4. Camera entity
5. For video: a camera that supports `camera.record`

## Integration

Repository:

`https://github.com/asustek1978/MAX-Messenger-Camera-Notifications-Photo-Video-Photo-Video`

Actions:

```text
max_messenger.send_message
max_messenger.broadcast
max_messenger.send_image
max_messenger.broadcast_image
max_messenger.send_video
max_messenger.broadcast_video
max_messenger.answer_callback
```

## Blueprint import

`https://github.com/asustek1978/MAX-Messenger-Camera-Notifications-Photo-Video-Photo-Video/blob/main/blueprints/automation/max_messenger/camera_notifications.yaml`

In Home Assistant open **Settings → Automations & scenes → Blueprints → Import blueprint**.

## Notes

The default output files use `/media`, so no personal paths or entity IDs are built into the blueprint. If **Video** or **Photo + video** is selected, verify `camera.record` works with your camera before using the blueprint.

Bug reports and improvements are welcome in the GitHub repository.
