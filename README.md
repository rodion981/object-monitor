# Object Event Monitor

Object Event Monitor is a Home Assistant custom integration that turns label-selected entity changes into Home Assistant events for automations.

It is useful for multi-site setups such as homes, cafes, restaurants, hotels, offices, warehouses, and other remote objects.

The integration is event-driven and uses Home Assistant labels. Label roles are configurable in the integration options:

- Availability monitoring watches selected entities for `unavailable` and recovery states. Default label: `device_monitoring`.
- Configured object labels, such as `home`, `restaurant`, or `cafe`, identify the monitored object.
- Optional category labels can route automation logic. Defaults: `security`, `light`, `climate`.
- Optional display names let events show human-friendly object and category names while labels remain stable Latin IDs.
- Security systems can be monitored with the `security_system` label.
- On/off state changes can be monitored with the `state_monitor` label.

The integration does not call notification scripts directly. It emits
`object_monitor_event`, and your Home Assistant automations decide how to notify
people.

Supported event types:

- `offline`
- `recovery`
- `security_state`
- `on_off_state`

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
7. Install **Object Event Monitor**.
8. Restart Home Assistant.

## Basic Setup

Add the integration from:

```text
Settings -> Devices & services -> Add integration -> Object Event Monitor
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

Automation trigger:

```yaml
triggers:
  - trigger: event
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

Use only one timeout label per entity. If no timeout label is present, Object Event Monitor uses the default timeout from the integration options.

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

## On/Off State Monitoring

To monitor normal `on` / `off` changes, add these labels to an entity:

```text
state_monitor
home
power
```

`home` must be one of the configured object labels. `power` should be one of
the configured category labels if you use the provided automation package with
`script.tg_<object>_<category>` routing.

On/off monitoring emits:

```yaml
event_type: on_off_state
entity_id: binary_sensor.home_power
friendly_name: Main Power
object_label: home
category: power
previous_state: off
state: on
```

## Services

The integration provides:

- `object_monitor.send_test_notification`
- `object_monitor.reload_monitored_entities`
- `object_monitor.clear_entity_state`

Use `object_monitor.send_test_notification` from Developer Tools to emit a test
`object_monitor_event` before testing real unavailable entities.
