# Object Monitor

Object Monitor is a Home Assistant custom integration for monitoring unavailable entities across multiple locations, sites, or customer objects and emitting Home Assistant events for automations.

The integration is event-driven and uses Home Assistant labels. Label roles are configurable in the integration options:

- Monitoring label selects entities for monitoring. Default: `device_monitoring`.
- Configured object labels, such as `home`, `restaurant`, or `cafe`, identify the monitored object.
- Optional category labels can route automation logic. Defaults: `security`, `light`, `climate`.
- Optional display names let events show human-friendly object and category names while labels remain stable Latin IDs.
- Security systems can be monitored with the `security_system` label.

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
home
restaurant
cafe
```

Optionally configure display names for emitted events:

```text
home=Home
restaurant=Restaurant
cafe=Cafe
```

And category display names:

```text
security=Security
power=Power
internet=Internet
```

Object Monitor does not call notification scripts directly. It emits the
`object_monitor_event` event and your Home Assistant automations decide how to
deliver notifications.

Automation trigger:

```yaml
trigger:
  - platform: event
    event_type: object_monitor_event
```

Then assign labels to monitored entities.

Object-only event example:

```text
device_monitoring
home
```

Categorized event example:

```text
device_monitoring
home
security
```

Per-entity timeout labels can override the default timeout:

```text
timeout_20s
timeout_7m
timeout_1h
```

Use only one timeout label per entity. If no timeout label is present, Object Monitor uses the default timeout from the integration options.

## Security System Monitoring

To monitor an alarm panel, add these labels to an `alarm_control_panel` entity:

```text
security_system
home
```

`home` must be one of the configured object labels.

Security state changes emit the same `object_monitor_event` event as
availability monitoring, with `event_type: security_state`.

Supported states include `disarmed`, `armed_home`, `armed_away`, `armed_night`, `armed_vacation`, `arming`, `pending`, `triggered`, `unknown`, and `unavailable`.

Version `v0.1.5` is the last release before security system monitoring and can be selected in HACS if you need to roll back.

## Services

The integration provides:

- `object_monitor.send_test_notification`
- `object_monitor.reload_monitored_entities`
- `object_monitor.clear_entity_state`

Use `object_monitor.send_test_notification` from Developer Tools to emit a test
`object_monitor_event` before testing real unavailable entities.
