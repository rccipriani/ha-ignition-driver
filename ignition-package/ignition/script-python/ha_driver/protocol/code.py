def auth(access_token):
    return {
        "type": "auth",
        "access_token": access_token
    }


def get_states():
    return {"type": "get_states"}


def subscribe_events(event_type=None):
    message = {"type": "subscribe_events"}
    if event_type:
        message["event_type"] = event_type
    return message


def call_service(domain, service, service_data=None, target=None,
                 return_response=False):
    message = {
        "type": "call_service",
        "domain": domain,
        "service": service,
        "service_data": service_data or {}
    }
    if target:
        message["target"] = target
    if return_response:
        message["return_response"] = True
    return message


def ping():
    return {"type": "ping"}


def parse_entity_state(raw_state):
    from ha_driver.models import EntityState

    if not raw_state:
        return None

    return EntityState(
        entity_id=raw_state.get("entity_id"),
        state=raw_state.get("state"),
        attributes=raw_state.get("attributes") or {},
        last_changed=raw_state.get("last_changed"),
        last_updated=raw_state.get("last_updated"),
        context=raw_state.get("context") or {}
    )
