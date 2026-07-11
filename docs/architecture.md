# Architecture

## Design rule

Only `ha_bridge.transport` is allowed to interact with the WebSocket object.

```text
Gateway startup
  -> runtime
      -> driver
          -> transport
          -> protocol
          -> subscriptions
          -> registry
          -> tags
          -> commands
```

## Module responsibilities

- `config.py`: Reads settings from Ignition tags and supplies defaults.
- `models.py`: Small mutable model objects suitable for Jython.
- `protocol.py`: Builds and validates Home Assistant WebSocket messages.
- `transport.py`: Socket lifecycle, authentication, request IDs, response correlation, reconnect logic, and outbound serialization.
- `subscriptions.py`: Tracks subscription IDs and normalizes events.
- `registry.py`: Maps Home Assistant entity IDs to stable Ignition tag paths.
- `tags.py`: Creates tags, writes state batches, and updates driver diagnostics.
- `commands.py`: Converts driver calls into Home Assistant `call_service` requests.
- `driver.py`: Coordinates initialization and routes normalized messages.
- `runtime.py`: Ensures one driver instance exists per Gateway project runtime.
- `bootstrap.py`: Gateway startup/shutdown entry points.

## Connection lifecycle

```text
STOPPED
  -> CONNECTING
  -> AUTHENTICATING
  -> INITIALIZING
  -> SUBSCRIBED
  -> ONLINE
```

On disconnect, the transport enters `RECONNECT_WAIT` and retries using bounded exponential backoff.

## Initialization sequence

1. Open `ws://homeassistant:8123/api/websocket`.
2. Receive `auth_required`.
3. Send the long-lived access token.
4. Receive `auth_ok`.
5. Send `get_states`.
6. Reconcile entity tags and write initial values.
7. Subscribe to `state_changed`.
8. Mark the driver `ONLINE` after Home Assistant confirms the subscription.

## Command path

```text
Ignition script or command tag
  -> commands.call_service()
  -> transport.send_request()
  -> Home Assistant result message
  -> pending request callback
  -> optional state confirmation from state_changed
```

A successful `call_service` response means Home Assistant accepted the service call. It does not necessarily prove that a physical device achieved the requested state.
