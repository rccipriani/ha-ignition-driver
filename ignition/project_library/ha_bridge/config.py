DEFAULT_TAG_ROOT = "[default]HomeAssistant"
DEFAULT_WS_URL = "ws://homeassistant:8123/api/websocket"


def _read(path, default=None):
    try:
        value = system.tag.readBlocking([path])[0]
        if value.quality.isGood():
            return value.value
    except Exception:
        pass
    return default


def _read_json(path, default):
    raw = _read(path, None)
    if raw in (None, ""):
        return default
    try:
        return system.util.jsonDecode(raw)
    except Exception:
        return default


def load():
    base = DEFAULT_TAG_ROOT + "/Configuration"
    root = _read(base + "/TagRoot", DEFAULT_TAG_ROOT)

    return {
        "enabled": bool(_read(base + "/Enabled", True)),
        "url": _read(base + "/WebSocketUrl", DEFAULT_WS_URL),
        "access_token": _read(base + "/AccessToken", ""),
        "tag_root": root,
        "include_domains": _read_json(base + "/IncludeDomainsJson", []),
        "exclude_domains": _read_json(
            base + "/ExcludeDomainsJson",
            ["automation", "event", "update"]
        ),
        "request_timeout_ms": 10000,
        "service_timeout_ms": 15000,
        "reconnect_initial_ms": 1000,
        "reconnect_max_ms": 60000,
        "reconnect_multiplier": 2.0,
        "tag_flush_ms": 200
    }
