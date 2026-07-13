from ha_driver.models import EntityMapping


def split_entity_id(entity_id):
    if not entity_id or "." not in entity_id:
        return "unknown", entity_id or "unknown"
    return entity_id.split(".", 1)


def encode_segment(value):
    value = str(value)
    replacements = [
        ("%", "%25"),
        ("/", "%2F"),
        ("[", "%5B"),
        ("]", "%5D")
    ]
    for old, new in replacements:
        value = value.replace(old, new)
    return value


class EntityRegistry(object):
    def __init__(self, tag_root, include_domains=None, exclude_domains=None):
        self.tag_root = tag_root.rstrip("/")
        self.include_domains = set(include_domains or [])
        self.exclude_domains = set(exclude_domains or [])
        self.by_entity_id = {}
        self.by_tag_path = {}

    def should_include(self, entity_id):
        domain, _ = split_entity_id(entity_id)
        if self.include_domains and domain not in self.include_domains:
            return False
        return domain not in self.exclude_domains

    def mapping_for(self, entity_id):
        existing = self.by_entity_id.get(entity_id)
        if existing:
            return existing

        domain, object_id = split_entity_id(entity_id)
        path = "%s/Entities/%s/%s" % (
            self.tag_root,
            encode_segment(domain),
            encode_segment(object_id)
        )
        mapping = EntityMapping(entity_id, path, domain, object_id)
        self.by_entity_id[entity_id] = mapping
        self.by_tag_path[path] = mapping
        return mapping

    def reconcile_states(self, states):
        mappings = []
        for state in states:
            if state and self.should_include(state.entity_id):
                mappings.append(self.mapping_for(state.entity_id))
        return mappings

    def count(self):
        return len(self.by_entity_id)
