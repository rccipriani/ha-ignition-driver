CONFIG_TAG_ROOT = "[default]HomeAssistantV2/Configuration"
DEFAULT_TAG_ROOT = "[default]HomeAssistantV2"
DEFAULT_WS_URL = "ws://192.168.1.91:8123/api/websocket"


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


def _read_access_token():
    """Read the Home Assistant long-lived token from Ignition Secrets."""
    try:
        with system.secrets.readSecretValue(
            "Ignition",
            "home-assistant-token"
        ) as secret:
            return secret.getSecretAsString()
    except Exception as exc:
        system.util.getLogger("ha_driver.config").error(
            "Unable to read Home Assistant access token: %s" % exc
        )
        return ""


def load():
    root = _read(
        CONFIG_TAG_ROOT + "/TagRoot",
        DEFAULT_TAG_ROOT
    )

    return {
        "enabled": bool(
            _read(CONFIG_TAG_ROOT + "/Enabled", False)
        ),
        "url": _read(
            CONFIG_TAG_ROOT + "/WebSocketUrl",
            DEFAULT_WS_URL
        ),
        "access_token": _read_access_token(),
        "tag_root": root,
        "include_domains": _read_json(
            CONFIG_TAG_ROOT + "/IncludeDomainsJson",
            []
        ),
        "exclude_domains": _read_json(
            CONFIG_TAG_ROOT + "/ExcludeDomainsJson",
            ["automation", "event", "update"]
        ),
        "request_timeout_ms": 10000,
        "service_timeout_ms": 15000,
        "reconnect_initial_ms": 1000,
        "reconnect_max_ms": 60000,
        "reconnect_multiplier": 2.0,
        "tag_flush_ms": 200
    }
