class PendingRequest(object):
    def __init__(self, request_id, command_type, created_ms, timeout_ms,
                 callback=None, context=None):
        self.request_id = request_id
        self.command_type = command_type
        self.created_ms = created_ms
        self.timeout_ms = timeout_ms
        self.callback = callback
        self.context = context or {}

    def is_expired(self, now_ms):
        return now_ms >= (self.created_ms + self.timeout_ms)


class EntityMapping(object):
    def __init__(self, entity_id, tag_path, domain, object_id,
                 writable=False, command_profile=None):
        self.entity_id = entity_id
        self.tag_path = tag_path
        self.domain = domain
        self.object_id = object_id
        self.writable = writable
        self.command_profile = command_profile


class EntityState(object):
    def __init__(self, entity_id, state, attributes=None, last_changed=None,
                 last_updated=None, context=None):
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes or {}
        self.last_changed = last_changed
        self.last_updated = last_updated
        self.context = context or {}
