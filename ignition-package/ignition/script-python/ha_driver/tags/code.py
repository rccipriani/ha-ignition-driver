def _json(value):
    try:
        return system.util.jsonEncode(value)
    except Exception:
        return "{}"


def typed_value(entity_state):
    state = entity_state.state
    domain = entity_state.entity_id.split(".", 1)[0]

    if state in (None, "unknown", "unavailable"):
        return None

    if domain in ("binary_sensor", "switch", "light", "input_boolean"):
        if state == "on":
            return True
        if state == "off":
            return False

    try:
        if "." in str(state):
            return float(state)
        return int(state)
    except Exception:
        return state


class TagManager(object):
    def __init__(self, tag_root):
        self.tag_root = tag_root.rstrip("/")
        self.logger = system.util.getLogger("ha_driver.tags")

    def ensure_driver_tags(self):
        provider_root, relative_root = self._split_provider(self.tag_root)
        base = relative_root + "/Driver"
        tags = [
            self._memory("Enabled", "Boolean", True),
            self._memory("ConnectionState", "String", "STOPPED"),
            self._memory("Connected", "Boolean", False),
            self._memory("Authenticated", "Boolean", False),
            self._memory("LastConnected", "DateTime", None),
            self._memory("LastMessage", "DateTime", None),
            self._memory("LastStateSync", "DateTime", None),
            self._memory("LastError", "String", ""),
            self._memory("ReconnectCount", "Int8", 0),
            self._memory("ReceivedMessages", "Int8", 0),
            self._memory("SentMessages", "Int8", 0),
            self._memory("PendingRequests", "Int4", 0),
            self._memory("EntityCount", "Int4", 0)
        ]
        system.tag.configure(provider_root + base, tags, "m")

    def ensure_entity(self, mapping, state):
        provider_root, relative = self._split_provider(mapping.tag_path)
        attrs = state.attributes or {}
        tags = [
            self._memory("EntityId", "String", state.entity_id),
            self._memory("Domain", "String", mapping.domain),
            self._memory("ObjectId", "String", mapping.object_id),
            self._memory("FriendlyName", "String", attrs.get("friendly_name", "")),
            self._memory("State", "String", state.state),
            self._memory("Value", self._data_type(typed_value(state)), typed_value(state)),
            self._memory("Available", "Boolean", state.state != "unavailable"),
            self._memory("LastChanged", "String", state.last_changed or ""),
            self._memory("LastUpdated", "String", state.last_updated or ""),
            self._memory("AttributesJson", "String", _json(attrs)),
            self._memory("Retired", "Boolean", False)
        ]
        system.tag.configure(provider_root + relative, tags, "m")

    def write_entity_state(self, mapping, state):
        base = mapping.tag_path
        paths = [
            base + "/FriendlyName",
            base + "/State",
            base + "/Value",
            base + "/Available",
            base + "/LastChanged",
            base + "/LastUpdated",
            base + "/AttributesJson",
            base + "/Retired"
        ]
        values = [
            state.attributes.get("friendly_name", ""),
            state.state,
            typed_value(state),
            state.state != "unavailable",
            state.last_changed or "",
            state.last_updated or "",
            _json(state.attributes),
            False
        ]
        system.tag.writeAsync(paths, values)

    def write_driver(self, name, value):
        system.tag.writeAsync([self.tag_root + "/Driver/" + name], [value])

    def write_driver_many(self, values):
        paths = []
        data = []
        for name, value in values.items():
            paths.append(self.tag_root + "/Driver/" + name)
            data.append(value)
        if paths:
            system.tag.writeAsync(paths, data)

    def _memory(self, name, data_type, value):
        config = {
            "name": name,
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": data_type
        }
        if value is not None:
            config["value"] = value
        return config

    def _data_type(self, value):
        if isinstance(value, bool):
            return "Boolean"
        if isinstance(value, int):
            return "Int8"
        if isinstance(value, float):
            return "Float8"
        return "String"

    def _split_provider(self, path):
        close = path.find("]")
        if not path.startswith("[") or close < 0:
            return "[default]", path
        return path[:close + 1], path[close + 1:]
