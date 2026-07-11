# Installation

## 1. Import project-library scripts

Create an Ignition Project Library package named `ha_bridge` and copy each Python module from:

```text
ignition/project_library/ha_bridge/
```

## 2. Create configuration tags

Create the following memory tags. The driver can create its runtime diagnostics and entity folders, but configuration should exist before startup.

```text
[default]HomeAssistant/Configuration/Enabled              Boolean  true
[default]HomeAssistant/Configuration/WebSocketUrl         String   ws://homeassistant:8123/api/websocket
[default]HomeAssistant/Configuration/AccessToken          String   <HA long-lived token>
[default]HomeAssistant/Configuration/TagRoot              String   [default]HomeAssistant
[default]HomeAssistant/Configuration/IncludeDomainsJson   String   []
[default]HomeAssistant/Configuration/ExcludeDomainsJson   String   ["automation","event","update"]
```

Restrict read access to the access-token tag. Do not expose it in Perspective views.

## 3. Add Gateway event scripts

Gateway Startup:

```python
ha_bridge.bootstrap.start()
```

Gateway Shutdown:

```python
ha_bridge.bootstrap.stop()
```

## 4. Verify operation

Browse:

```text
[default]HomeAssistant/Driver
```

Expected values:

- `Connected`: true
- `Authenticated`: true
- `ConnectionState`: `ONLINE`
- `EntityCount`: greater than zero
- `LastMessage`: updates during Home Assistant activity

## 5. Test a command

From the Ignition Script Console in Gateway scope:

```python
ha_bridge.commands.call_service(
    domain="input_boolean",
    service="turn_on",
    target={"entity_id": "input_boolean.ignition_test"}
)
```

## WebSocket implementation

The starter transport uses the Java-WebSocket library when it is present on the Ignition Gateway classpath. If your Ignition installation does not expose `org.java_websocket.client.WebSocketClient`, install an approved WebSocket client library or adapt `transport.py` to the WebSocket implementation already used by the current `ha_bridge` script.
