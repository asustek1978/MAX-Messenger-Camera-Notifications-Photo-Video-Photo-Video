# [Blueprint] MAX Messenger camera notifications — photo, video or both

Send camera events from Home Assistant to **MAX Messenger**.

This blueprint works with the **Slava MAX** custom integration and supports:

- Photo + video
- Photo only
- Video only
- Any Home Assistant trigger
- Optional conditions
- Configurable video duration
- Multiple MAX recipients
- ACL-aware broadcast (`notifications` + `cameras`)
- A `🏠 Smart Home` callback button below notifications

## Requirements

- Home Assistant 2024.6.0+
- Slava MAX 0.5.5+
- A MAX bot configured in Slava MAX
- For video: a camera entity that supports `camera.record`

## Installation

Install the Slava MAX integration from the GitHub repository, then import or
copy the blueprint:

`blueprints/automation/slava_max/camera_snapshot_max.yaml`

After importing it, create a new automation and select:

1. your trigger (motion/person/doorbell/etc.);
2. your camera;
3. Photo + video / Photo only / Video only;
4. optional MAX user IDs and permissions.

If the MAX recipients field is empty, Slava MAX broadcasts to all enabled
users that have the required permissions.

## Notes

The blueprint does not contain any installation-specific entity IDs.
Default files are stored under `/media`.

For video recording, `camera.record` must work for the selected camera.

## Project

GitHub: https://github.com/asustek1978/MAX-Messenger-Camera-Notifications-Photo-Video-Photo-Video

Feedback, traces and camera compatibility reports are welcome.
