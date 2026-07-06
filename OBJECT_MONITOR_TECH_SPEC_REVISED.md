# Object Monitor Integration

## Technical Specification v1.2

## 1. Overview

Object Monitor is a Home Assistant custom integration that detects operational events for monitored objects and emits provider-neutral Home Assistant events.

The integration does not deliver Telegram, push, or other notifications directly. Delivery is handled by Home Assistant automations and scripts that listen for `object_monitor_event`.

## 2. Core Responsibilities

Object Monitor is responsible for:

- selecting entities by Home Assistant labels
- detecting entity availability incidents
- tracking per-entity unavailable timeout state
- detecting security system state changes
- emitting normalized Home Assistant events
- preserving availability incident context across Home Assistant restarts

Object Monitor is not responsible for:

- formatting final user-facing notification messages
- choosing Telegram groups or topics
- calling Telegram scripts directly
- routing messages to external services
- managing notification delivery retries

## 3. Event Model

All monitor output is emitted through the Home Assistant event bus:

```text
object_monitor_event
```

Automations should listen for this event and inspect `trigger.event.data`.

Availability events use:

```yaml
event_type: offline
entity_id: sensor.example
friendly_name: Example
object_label: home
category: power
timeout_seconds: 420
```

Recovery events use:

```yaml
event_type: recovery
entity_id: sensor.example
friendly_name: Example
object_label: home
category: power
```

Security events use:

```yaml
event_type: security_state
entity_id: alarm_control_panel.home
friendly_name: Security System
object_label: home
category: security
previous_state: disarmed
state: armed_away
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

When a monitored entity becomes `unavailable` or `unknown`, Object Monitor:

1. resolves labels and display names
2. stores the incident start time
3. schedules a timeout
4. emits `event_type: offline` only if the entity remains unavailable after the timeout

When the entity returns to a normal state, Object Monitor:

1. cancels any pending timeout
2. emits `event_type: recovery` only if an offline event was already emitted
3. clears stored incident state

Storage is required for availability incidents so that Home Assistant restarts do not reset pending timeout windows or duplicate offline/recovery events.

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

Security monitoring emits `event_type: security_state` when the state actually changes.

On startup, the current state is treated as the baseline and does not emit a notification event. If the first observed state change includes an `old_state`, Object Monitor emits the event using that previous state.

## 8. Automation Routing

Notification delivery should be implemented in Home Assistant automations.

A typical automation trigger:

```yaml
trigger:
  - platform: event
    event_type: object_monitor_event
```

Automations can route by:

```yaml
{{ trigger.event.data.event_type }}
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

## 9. Services

The integration provides:

- `object_monitor.send_test_notification`
- `object_monitor.reload_monitored_entities`
- `object_monitor.clear_entity_state`

`send_test_notification` is kept for backward compatibility with earlier releases. It now emits a test `object_monitor_event` instead of sending a direct notification.

## 10. Architecture

Main modules:

- `config_flow.py` handles configuration and options
- `label_resolver.py` resolves monitoring, object, category, and timeout labels
- `monitor.py` watches availability-related state changes
- `entity_tracker.py` tracks pending/offline availability incidents
- `security_monitor.py` watches security system state changes
- `storage.py` persists availability incident state
- `notification_manager.py` acknowledges emitted events without external delivery
- `runtime.py` composes runtime services and monitors
- `services.py` exposes Home Assistant services

## 11. Compatibility

The integration is designed for Home Assistant custom integration deployment through HACS.

The README is the primary HACS-rendered documentation.

Release notes should call out that direct Telegram delivery was removed and replaced with event-only automation routing.
