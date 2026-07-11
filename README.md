# Home Assistant Driver for Ignition

A reusable Home Assistant WebSocket driver for Inductive Automation Ignition.

This project is designed for the **Home-as-a-Plant** lab and targets Ignition 8.3.x. It uses one persistent Home Assistant WebSocket connection for:

- Authentication
- Initial state synchronization
- `state_changed` subscriptions
- Automatic entity-to-tag mapping
- Bidirectional Home Assistant service calls
- Request/response correlation
- Reconnection and diagnostics

## Status

This repository is a functional starter implementation. The transport, protocol, registry, subscription, tag-writing, command, and runtime concerns are separated so the bridge can evolve into a maintainable driver.

## Repository layout

```text
ignition/project_library/ha_bridge/  Ignition project-library scripts
ignition/gateway_events/             Gateway startup/shutdown examples
docs/                                Architecture and installation notes
examples/                            Example command usage
Tests/                               CPython-compatible unit tests for pure logic
```

## Quick start

1. Create an Ignition project named for the driver or add the scripts to your existing project.
2. Copy the modules under `ignition/project_library/ha_bridge` into the Ignition Project Library as package `ha_bridge`.
3. Create the configuration tags described in `docs/installation.md`.
4. Add the Gateway startup and shutdown scripts.
5. Save the project and verify `[default]HomeAssistant/Driver/ConnectionState` becomes `ONLINE`.

## Important compatibility note

Ignition gateway scripting uses Jython. The code intentionally avoids Python 3-only syntax such as f-strings, annotations, dataclasses, and `asyncio`.

## Security

Do not commit a Home Assistant long-lived access token. Store it in a restricted Ignition memory tag or another Gateway-only secret mechanism.

## License

MIT. See `LICENSE`.
