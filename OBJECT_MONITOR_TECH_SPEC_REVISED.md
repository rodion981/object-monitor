# Object Monitor Integration

## Technical Specification v1.1

---

## 1. Overview

Develop a production-ready Home Assistant custom integration named **Object Monitor**.

The integration monitors selected Home Assistant entities across multiple customer objects such as restaurants, cafes, hotels, offices, warehouses, and other remote facilities.

The integration detects entities that become `unavailable`, waits for a configurable grace period, sends routed notifications when the entity remains offline, and sends recovery notifications when the entity returns online.

This project is not a Home Assistant automation. It must be implemented as a native Home Assistant custom integration using Config Entry, Options Flow, asynchronous lifecycle handling, registries, event helpers, and persistent runtime state.

---

## 2. Design Goals

The integration must be:

- event driven
- asynchronous
- production ready
- modular
- scalable for many entities and many customer objects
- independent from Telegram-specific logic in the monitoring core
- compatible with current Home Assistant Core architecture
- safe across Home Assistant restarts
- easy to extend with new notification providers and future features

Polling is not allowed for normal monitoring.

A one-time startup reconciliation is allowed and required. It must inspect current Home Assistant states and registries during integration setup to restore monitoring state after restart.

---

## 3. Home Assistant Architecture Requirements

The integration must use:

- Config Entry
- Options Flow
- `ConfigEntry.runtime_data` for runtime objects
- asyncio-compatible code only
- Entity Registry
- Label Registry
- Device Registry where relevant for diagnostics and future support
- Area Registry for future routing support
- Home Assistant event helpers for state tracking
- persistent storage through Home Assistant storage helpers
- diagnostics support
- clean unload support

The integration must avoid:

- blocking I/O
- global mutable runtime state
- polling loops
- hardcoded object names
- hardcoded Telegram script names beyond the documented routing pattern
- direct Config Entry mutation
- notification-provider logic inside the monitoring engine

---

## 4. Monitoring Selection

Only entities with the label `device_monitoring` participate in monitoring.

Entities without `device_monitoring` must be ignored.

The integration must react to relevant registry changes so that adding or removing `device_monitoring` can take effect without a Home Assistant restart whenever possible.

---

## 5. Object Identification

Every monitored entity must belong to exactly one monitored object.

Object detection must not depend on label order.

### 5.1 Object Labels

To avoid ambiguity with future labels such as `critical`, `ups`, `camera`, `wifi`, `zigbee`, or `maintenance`, object labels must be explicitly configured.

The Options Flow must include a configurable list of object labels.

Example object labels:

- `qirim`
- `karavan`
- `hotel_kyiv`
- `office_center`

For an entity to be valid:

- it must have `device_monitoring`
- it must have exactly one label from the configured object label list

If no configured object label is found:

- log a warning
- skip monitoring for that entity

If more than one configured object label is found:

- log a warning
- skip monitoring for that entity

### 5.2 Future Option

A future version may support object labels with an explicit namespace such as `object_qirim` or `om_object_qirim`, but v1.1 uses a configured allow-list to remain compatible with existing labels.

---

## 6. Categories

Categories are used only for notification routing and message context.

Supported category labels:

- `security`
- `light`
- `climate`

The category label is not required for basic monitoring.

The category label is required only when `category_routing` mode is enabled, because it determines which Telegram group topic or branch receives the notification.

If Category Routing is enabled and a monitored entity has no supported category:

- log a warning
- skip notification for that event
- keep monitoring active

If Single Routing is enabled and category is missing:

- send the notification through the object route
- omit the category from the message or display it as `unknown`

If Single Routing is enabled and category is present:

- send the notification through the object route
- include the category in the message text only as context

If more than one supported category is present:

- log a warning
- skip notification for that event
- keep monitoring active

Unknown labels must not affect monitoring.

---

## 7. Monitoring Behavior

The integration must listen for state changes of monitored entities.

When a monitored entity becomes `unavailable`:

1. Store the `unavailable_since` timestamp.
2. Start a grace-period timer.
3. Do not send a notification immediately.

Default timeout:

- 420 seconds

If the entity recovers before the timer expires:

1. Cancel the timer.
2. Clear the pending unavailable state.
3. Do not send a notification.

If the timer expires:

1. Check the current entity state again.
2. If the entity is still `unavailable`, mark it offline.
3. Persist the offline/notified state.
4. Emit an internal monitor event.
5. Send one offline notification.

Duplicate offline notifications for the same uninterrupted outage are forbidden.

When an offline entity returns online:

1. Check whether an offline notification was previously sent.
2. Send a recovery notification only if an offline notification was sent.
3. Remove the entity from the offline list.
4. Persist the updated state.

---

## 8. Restart Handling

Restart handling is mandatory.

The integration must persist enough state to avoid duplicate notifications after Home Assistant or integration restart.

Persistent state must include:

- entity ID
- object label
- category label, if known
- `unavailable_since`
- offline/notified flag
- last notification event type

On setup:

1. Load persisted monitor state.
2. Reconcile it with current Home Assistant states.
3. Restore offline entities without resending offline notifications.
4. Restore pending timers when possible.
5. If an entity recovered while Home Assistant was offline and an offline notification had been sent, send one recovery notification after reconciliation.
6. Remove stale persisted entries for entities that no longer exist or are no longer monitored.

Startup reconciliation is not considered polling.

---

## 9. Notification Architecture

The monitoring engine must not know anything about Telegram.

The monitor produces provider-neutral notification events.

Example event:

```python
NotificationEvent(
    object_label="qirim",
    category="security",
    event_type="offline",
    entity_id="binary_sensor.router",
    friendly_name="Main Router",
)
```

`NotificationManager` receives these events and delegates delivery to the selected notification provider.

---

## 10. Notification Providers

Create a provider interface named `NotificationProvider`.

The interface must support asynchronous sending.

Initial provider:

- `TelegramProvider`

Future providers must be possible without changing monitor logic:

- Discord
- Webhook
- Signal
- Slack
- Microsoft Teams
- Email

---

## 11. Telegram Provider

The Telegram provider must deliver notifications by calling Home Assistant scripts.

The provider must support two routing modes.

### 11.1 Category Routing

Script format:

```text
script.tg_<object>_<category>
```

Examples:

```text
script.tg_qirim_security
script.tg_qirim_light
script.tg_qirim_climate
```

This mode is intended for Telegram forums or topic-based routing.

In this mode, the category label selects the Telegram topic or branch.

If category is missing or invalid:

- log a warning
- skip notification

### 11.2 Single Routing

Script format:

```text
script.tg_<object>
```

Examples:

```text
script.tg_qirim
script.tg_hotel_kyiv
```

This mode is intended for customers without Telegram topics.

Category must be displayed inside notification text when available. If missing, display `unknown`.

In this mode, category does not affect routing.

### 11.3 Missing Scripts

If a target script is missing:

- log a warning
- do not crash
- do not stop monitoring
- do not mark the notification as successfully delivered

---

## 12. Notification Messages

### 12.1 Offline

```text
🔴 <Friendly Name>

Entity
<entity_id>

Object
<object>

Category
<category>

Unavailable for more than <timeout>.
```

### 12.2 Recovery

```text
🟢 <Friendly Name>

Recovered.

Entity
<entity_id>

Object
<object>

Category
<category>
```

Message formatting must be provider-owned or delegated to a notification formatting helper. The monitor must not format Telegram-specific messages.

---

## 13. Configuration

The integration must be set up from the Home Assistant UI.

### 13.1 Config Entry

The config flow must prevent duplicate setup of the integration.

No YAML configuration is required for v1.1.

### 13.2 Options Flow

Options:

- monitoring timeout, default `420`
- notification mode:
  - `category_routing`
  - `single_routing`
- configured object labels
- debug logging
- notification provider, initially only `telegram`
- future heartbeat interval, stored but not active unless implemented

Validation:

- timeout must be a positive integer
- object labels must be non-empty normalized strings
- notification mode must be one of the supported modes

Changing options must reload or reconfigure runtime behavior safely.

---

## 14. Internal Modules

Recommended file structure:

```text
custom_components/object_monitor/
  manifest.json
  __init__.py
  config_flow.py
  const.py
  models.py
  runtime.py
  monitor.py
  entity_tracker.py
  label_resolver.py
  notification_manager.py
  storage.py
  services.py
  diagnostics.py
  providers/
    __init__.py
    base.py
    telegram.py
  translations/
    en.json
  tests/
```

### 14.1 `manifest.json`

Declares the integration metadata so Home Assistant can load it.

Must include:

- domain
- name
- version
- config flow support
- integration type
- requirements, if any

### 14.2 `__init__.py`

Owns integration lifecycle.

Responsibilities:

- `async_setup_entry`
- `async_unload_entry`
- create runtime object
- store runtime object in `entry.runtime_data`
- register unload callbacks
- register services if needed
- cleanly stop listeners and timers on unload

### 14.3 `config_flow.py`

Provides UI setup and Options Flow.

Responsibilities:

- create the Config Entry
- prevent duplicate setup
- expose runtime options
- validate user input
- trigger reload when options change

### 14.4 `const.py`

Contains constants only.

Examples:

- domain
- option keys
- default timeout
- notification modes
- supported category labels
- monitor label
- storage version/key
- event names

### 14.5 `models.py`

Contains typed dataclasses and enums.

Examples:

- `MonitorConfig`
- `EntityLabels`
- `MonitoredEntity`
- `NotificationEvent`
- `NotificationEventType`
- `NotificationMode`
- `ProviderType`
- `StoredMonitorState`

### 14.6 `runtime.py`

Contains the top-level runtime container for one Config Entry.

Responsibilities:

- compose monitor, storage, label resolver, notification manager, providers
- start components in the correct order
- stop components in reverse order
- provide diagnostics data

This replaces the ambiguous `coordinator.py`. The integration is event-driven and should not imply a polling coordinator.

### 14.7 `monitor.py`

Contains `ObjectMonitor`.

Responsibilities:

- subscribe to state changes
- perform startup reconciliation
- delegate per-entity state to `EntityTracker`
- emit provider-neutral events
- respond to registry changes

The monitor must not call Telegram scripts directly.

### 14.8 `entity_tracker.py`

Contains entity-level state tracking.

Responsibilities:

- track pending timers
- cancel timers safely
- prevent duplicate offline notifications
- detect valid recovery notifications
- manage per-entity in-memory state

### 14.9 `label_resolver.py`

Resolves monitored entity metadata from Home Assistant labels.

Responsibilities:

- check `device_monitoring`
- resolve exactly one configured object label
- resolve zero or one category label
- ignore unrelated labels
- return structured result or a reason why the entity is not monitorable

### 14.10 `notification_manager.py`

Provider-neutral notification orchestration.

Responsibilities:

- receive `NotificationEvent`
- select configured provider
- call provider asynchronously
- log delivery failures without stopping monitor logic

### 14.11 `storage.py`

Persistent monitor state.

Responsibilities:

- load stored state during setup
- save offline and pending states
- debounce writes if needed
- clear stale entities
- support future migrations

### 14.12 `providers/base.py`

Defines the provider interface.

Responsibilities:

- base async contract for sending notifications
- provider result type if needed

### 14.13 `providers/telegram.py`

Telegram script-based provider.

Responsibilities:

- build target script entity ID
- validate script availability
- format Telegram message
- call Home Assistant script service asynchronously
- log missing scripts or failed service calls

### 14.14 `helpers.py`

Optional utility module.

Use only for small pure helper functions. Do not place large business logic here.

### 14.15 `services.py`

Optional v1.1 services:

- send test notification
- reload monitored entities
- clear stored state for one entity
- list monitored entities

Services must raise Home Assistant service exceptions for user-facing failures.

### 14.16 `diagnostics.py`

Provides diagnostic data.

Must include:

- configured options, redacted if needed
- number of monitored entities
- number of offline entities
- number of pending timers
- provider type
- notification mode
- object labels
- recent non-sensitive warnings if practical

Must not expose secrets.

---

## 15. Events

The integration may fire a Home Assistant event for user automation and debugging.

Event name:

```text
object_monitor_event
```

Payload:

- `event_type`
- `entity_id`
- `friendly_name`
- `object_label`
- `category`
- `unavailable_since`
- `notified_at`

Internal module communication should not depend on the Home Assistant event bus. Direct async callbacks or dispatcher-style communication are preferred for internal flow.

---

## 16. Race Conditions and Safety

The integration must handle:

- entity recovers exactly when timer expires
- duplicate state changes
- missing `old_state`
- unavailable entity removed from registry
- labels changed while timer is active
- options changed while timers are active
- Home Assistant stopping while timers are active
- notification script missing
- notification service call failure

Timers must always re-check the current state before sending notifications.

All created listeners and timers must be cancelled on unload.

---

## 17. Future Features

The architecture must allow:

- heartbeat checks
- maintenance mode
- notification aggregation
- critical priority
- per-object configuration
- notification cooldown
- acknowledgement flow
- history
- statistics
- dashboard sensors
- multiple simultaneous notification providers
- SLA reports
- availability reports
- maintenance windows
- area-based routing
- device-based routing

These features must not be implemented as placeholders in v1.1.

---

## 18. Code Quality

Code requirements:

- type hints
- dataclasses where appropriate
- clear async boundaries
- structured logging
- docstrings for public classes and important methods
- focused classes
- no duplicated logic
- no hardcoded customer object names
- no blocking operations
- no placeholder code
- no broad exception swallowing without logging
- tests for core behavior

---

## 19. Testing Requirements

Tests must cover:

- config flow creates one entry only
- options validation
- label resolution
- entity without `device_monitoring` is ignored
- entity with no object label is skipped
- entity with multiple object labels is skipped
- category routing with missing category skips notification
- single routing with missing category sends notification as `unknown`
- unavailable entity recovers before timeout
- unavailable entity remains unavailable after timeout
- duplicate offline notification prevention
- recovery notification after offline notification
- no recovery notification if offline notification was never sent
- restart restores offline state without duplicate offline notification
- restart restores pending timer where possible
- missing Telegram script logs warning and does not crash
- unload cancels listeners and timers

---

## 20. Development Process

Generate the integration step by step.

Before generating each file:

1. Explain why the file exists.
2. Explain its responsibilities.
3. Explain how it interacts with other modules.

Then generate complete production-ready code for that file.

Do not generate placeholder modules.

Wait for confirmation before generating the next file unless the user explicitly requests batch generation.

When implementation begins, start with:

1. `manifest.json`
2. `const.py`
3. `models.py`
4. `config_flow.py`
5. `storage.py`
6. `label_resolver.py`
7. `providers/base.py`
8. `providers/telegram.py`
9. `notification_manager.py`
10. `entity_tracker.py`
11. `monitor.py`
12. `runtime.py`
13. `__init__.py`
14. `diagnostics.py`
15. `services.py`, if needed
16. translations
17. tests
