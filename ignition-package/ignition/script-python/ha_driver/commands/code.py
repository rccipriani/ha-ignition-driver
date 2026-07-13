import uuid

from ha_driver import protocol


_driver_getter = None


def configure_driver_getter(getter):
    global _driver_getter
    _driver_getter = getter


def _driver():
    if _driver_getter is None:
        from ha_driver import runtime
        return runtime.get_driver()
    return _driver_getter()


def call_service(domain, service, service_data=None, target=None,
                 callback=None, timeout_ms=None):
    driver = _driver()
    if driver is None:
        raise RuntimeError("Home Assistant driver is not running")

    command_id = str(uuid.uuid4())
    message = protocol.call_service(
        domain,
        service,
        service_data=service_data,
        target=target
    )

    context = {
        "command_id": command_id,
        "domain": domain,
        "service": service,
        "target": target or {},
        "service_data": service_data or {}
    }

    driver.transport.send_request(
        message,
        callback=callback,
        timeout_ms=timeout_ms or driver.config.get("service_timeout_ms", 15000),
        context=context
    )
    return command_id


def turn_on(entity_id, service_data=None):
    domain = entity_id.split(".", 1)[0]
    return call_service(
        domain,
        "turn_on",
        service_data=service_data,
        target={"entity_id": entity_id}
    )


def turn_off(entity_id, service_data=None):
    domain = entity_id.split(".", 1)[0]
    return call_service(
        domain,
        "turn_off",
        service_data=service_data,
        target={"entity_id": entity_id}
    )
