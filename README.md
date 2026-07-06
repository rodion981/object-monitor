# Object Monitor

Object Monitor is a Home Assistant custom integration for monitoring unavailable entities across multiple customer objects.

The integration is event-driven and uses Home Assistant labels. Label roles are configurable in the integration options:

- Monitoring label selects entities for monitoring. Default: `device_monitoring`.
- Configured object labels, such as `qirim` or `hotel_kyiv`, identify the monitored object.
- Optional category labels can route notifications to Telegram topics. Defaults: `security`, `light`, `climate`.

## Installation with HACS

1. Open HACS.
2. Go to **Integrations**.
3. Open the three-dot menu.
4. Select **Custom repositories**.
5. Add this repository URL:

   ```text
   https://github.com/rodion981/object-monitor
   ```

6. Select category **Integration**.
7. Install **Object Monitor**.
8. Restart Home Assistant.

## Basic Setup

Add the integration from:

```text
Settings -> Devices & services -> Add integration -> Object Monitor
```

Configure label roles:

- Monitoring label: `device_monitoring`
- Category labels: `security`, `light`, `climate`, or your own labels
- Object labels, for example:

```text
qirim
karavan
hotel_kyiv
```

For single Telegram routing, create scripts like:

```text
script.tg_qirim
script.tg_karavan
```

For category routing, create scripts like:

```text
script.tg_qirim_security
script.tg_qirim_light
script.tg_qirim_climate
```

Then assign labels to monitored entities.

Single routing example:

```text
device_monitoring
qirim
```

Category routing example:

```text
device_monitoring
qirim
security
```

## Services

The integration provides:

- `object_monitor.send_test_notification`
- `object_monitor.reload_monitored_entities`
- `object_monitor.clear_entity_state`

Use `object_monitor.send_test_notification` from Developer Tools to verify Telegram routing before testing real unavailable entities.
