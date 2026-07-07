# Object Event Monitor Integration

## Technical Specification v1.2

## 1. Overview

Object Event Monitor is a Home Assistant custom integration that detects operational events for monitored objects and emits provider-neutral Home Assistant events.

The integration does not deliver Telegram, push, or other notifications directly. Delivery is handled by Home Assistant automations and scripts that listen for dedicated Object Event Monitor events.

## 2. Core Responsibilities

Object Event Monitor is responsible for:

- selecting entities by Home Assistant labels
- detecting entity availability incidents
- exposing per-object availability problem binary sensors
- tracking per-entity unavailable timeout state
- detecting security system state changes
- detecting selected on/off state changes
- emitting normalized Home Assistant events
- preserving availability incident context across Home Assistant restarts

Object Event Monitor is not responsible for:

- formatting final user-facing notification messages
- choosing Telegram groups or topics
- calling Telegram scripts directly
- routing messages to external services
- managing notification delivery retries

## 3. Event Model

All monitor output is emitted through the Home Assistant event bus as dedicated event types:

```text
object_monitor_offline
object_monitor_recovery
object_monitor_security_state
object_monitor_on_off_state
```

Automations should listen for the specific event they need and inspect `trigger.event.data`.

Availability events use:

```yaml
ha_event_type: object_monitor_offline
data:
  event_type: offline
  entity_id: sensor.example
  friendly_name: Example
  object_label: home
  category: power
  timeout_seconds: 420
```

Recovery events use:

```yaml
ha_event_type: object_monitor_recovery
data:
  event_type: recovery
  entity_id: sensor.example
  friendly_name: Example
  object_label: home
  category: power
```

Security events use:

```yaml
ha_event_type: object_monitor_security_state
data:
  event_type: security_state
  entity_id: alarm_control_panel.home
  friendly_name: Security System
  object_label: home
  category: security
  previous_state: disarmed
  state: armed_away
```

On/off state events use:

```yaml
ha_event_type: object_monitor_on_off_state
data:
  event_type: on_off_state
  entity_id: binary_sensor.home_power
  friendly_name: Main Power
  object_label: home
  category: power
  previous_state: off
  state: on
```

## 4. Label Model

The integration uses configurable Home Assistant labels.

Availability monitoring requires:

```text
<monitoring_label>
<one object label>
```

The default monitoring label is:

```text
device_monitoring
```

Optional category labels can be added:

```text
power
internet
security
```

Object labels identify the monitored location or customer object:

```text
home
restaurant
cafe
```

Each monitored entity must have exactly one configured object label.

## 5. Per-Entity Timeout Labels

The default timeout is configured in the integration options.

Individual entities may override it with one timeout label:

```text
timeout_20s
timeout_7m
timeout_1h
```

Supported suffixes:

- `s` seconds
- `m` minutes
- `h` hours

If multiple timeout labels are present, the entity is skipped and a warning is logged.

## 6. Availability Monitoring

Availability monitoring is event-driven.

When a monitored entity becomes `unavailable` or `unknown`, Object Event Monitor:

1. resolves labels and display names
2. stores the incident start time
3. schedules a timeout
4. emits `object_monitor_offline` only if the entity remains unavailable after the timeout

When the entity returns to a normal state, Object Event Monitor:

1. cancels any pending timeout
2. emits `object_monitor_recovery` only if an offline event was already emitted
3. clears stored incident state

Storage is required for availability incidents so that Home Assistant restarts do not reset pending timeout windows or duplicate offline/recovery events.

## 6.1 Object Availability Problem Sensors

For each configured object label, Object Event Monitor creates one binary sensor with
Home Assistant's `problem` device class.

The sensor is derived only from confirmed availability offline state:

- `off`: no confirmed offline availability entities exist for the object
- `on`: at least one confirmed offline availability entity exists for the object

Pending timeout state does not turn the sensor on. Security monitoring and
on/off state monitoring do not affect this aggregate sensor.

The sensor exposes diagnostic attributes:

```yaml
object_label: home
object_name: Home
monitored_count: 12
offline_count: 1
pending_count: 0
offline_entities:
  - sensor.home_router
pending_entities: []
```

## 7. Security Monitoring

Security monitoring is independent from availability monitoring.

Security entities are selected by labels:

```text
security_system
<one object label>
```

Initially supported domain:

```text
alarm_control_panel
```

Supported states:

- `disarmed`
- `armed_home`
- `armed_away`
- `armed_night`
- `armed_vacation`
- `arming`
- `pending`
- `triggered`
- `unknown`
- `unavailable`

Security monitoring emits `object_monitor_security_state` when the state actually changes.

On startup, the current state is treated as the baseline and does not emit an event. If the first observed state change includes an `old_state`, Object Event Monitor emits the event using that previous state.

## 8. On/Off State Monitoring

On/off state monitoring is independent from availability and security monitoring.

Entities are selected by labels:

```text
state_monitor
<one object label>
<optional category label>
```

Supported states:

- `on`
- `off`

The default ON/OFF state values are configurable in the integration options.
Default values are:

```text
ON: on
OFF: off
```

Users may add localized or integration-specific values, for example:

```text
ON:
on
увімкнено

OFF:
off
вимкнено
```

Object Event Monitor normalizes configured ON values to `state: on` and configured
OFF values to `state: off` in emitted events.

On startup, the current state is treated as the baseline and does not emit an event.

When a selected entity changes from `off` to `on` or from `on` to `off`, Object Event Monitor emits:

```yaml
event_type: object_monitor_on_off_state
event_data:
  event_type: on_off_state
  previous_state: off
  state: on
```

This feature is intended for binary sensors, switches, input booleans, and other Home Assistant entities that expose normal `on` / `off` states.

## 9. Automation Routing

Notification delivery should be implemented in Home Assistant automations.

A typical automation trigger:

```yaml
trigger:
  - platform: event
    event_type: object_monitor_offline
```

Automations can route by:

```yaml
{{ trigger.event.data.object_label }}
{{ trigger.event.data.category }}
{{ trigger.event.data.entity_id }}
{{ trigger.event.data.state }}
```

Example dynamic script target:

```yaml
target_script: >
  {% set object = trigger.event.data.object_label %}
  {% set category = trigger.event.data.category | default('', true) %}
  {% if category %}
    script.tg_{{ object }}_{{ category }}
  {% else %}
    script.tg_{{ object }}
  {% endif %}
```

This routing belongs to the user automation layer, not the integration.

## 10. Services

The integration provides:

- `object_monitor.send_test_notification`
- `object_monitor.reload_monitored_entities`
- `object_monitor.clear_entity_state`

`send_test_notification` is kept for backward compatibility with earlier releases. It now emits a test `object_monitor_offline` or `object_monitor_recovery` event instead of sending a direct notification.

## 11. Architecture

Main modules:

- `config_flow.py` handles configuration and options
- `label_resolver.py` resolves monitoring, object, category, and timeout labels
- `monitor.py` watches availability-related state changes
- `entity_tracker.py` tracks pending/offline availability incidents
- `security_monitor.py` watches security system state changes
- `on_off_monitor.py` watches selected on/off state changes
- `storage.py` persists availability incident state
- `notification_manager.py` acknowledges emitted events without external delivery
- `runtime.py` composes runtime services and monitors
- `services.py` exposes Home Assistant services

## 12. Compatibility

The integration is designed for Home Assistant custom integration deployment through HACS.

The README is the primary HACS-rendered documentation.

Release notes should call out that direct Telegram delivery was removed and replaced with event-only automation routing.
