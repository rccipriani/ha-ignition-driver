def start():
    from ha_driver import config
    from ha_driver import runtime

    settings = config.load()
    logger = system.util.getLogger("ha_driver.bootstrap")

    if not settings.get("enabled"):
        logger.info("Home Assistant driver is disabled")
        return None

    if not settings.get("access_token"):
        raise RuntimeError("Home Assistant access token is not configured")

    logger.info("Starting Home Assistant WebSocket driver")
    return runtime.start(settings)


def stop():
    from ha_driver import runtime
    system.util.getLogger("ha_driver.bootstrap").info(
        "Stopping Home Assistant WebSocket driver"
    )
    runtime.stop()
