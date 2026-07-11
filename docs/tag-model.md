# Tag model

## Driver diagnostics

```text
[default]HomeAssistant/Driver/
  Enabled
  ConnectionState
  Connected
  Authenticated
  LastConnected
  LastMessage
  LastStateSync
  LastError
  ReconnectCount
  ReceivedMessages
  SentMessages
  PendingRequests
  EntityCount
```

## Entity tags

An entity such as `sensor.garage_temperature` maps to:

```text
[default]HomeAssistant/Entities/sensor/garage_temperature/
  EntityId
  Domain
  ObjectId
  FriendlyName
  State
  Value
  Available
  LastChanged
  LastUpdated
  AttributesJson
  Retired
```

`State` always preserves Home Assistant's string state. `Value` is a best-effort typed representation.

## Mapping stability

The entity ID is the external identity. Friendly names are metadata only and may change without moving the tag path.

## Deletion policy

Entities absent during a later reconciliation are marked `Retired=true` and `Available=false`. They are not automatically deleted, protecting history and downstream bindings.
