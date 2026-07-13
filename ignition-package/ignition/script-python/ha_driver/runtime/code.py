from java.util.concurrent.locks import ReentrantLock

_DRIVER = None
_LOCK = ReentrantLock()


def start(config):
    global _DRIVER
    from ha_driver.driver import HomeAssistantDriver

    _LOCK.lock()
    try:
        if _DRIVER is not None:
            try:
                _DRIVER.stop()
            except Exception:
                pass
        _DRIVER = HomeAssistantDriver(config)
        _DRIVER.start()
        return _DRIVER
    finally:
        _LOCK.unlock()


def stop():
    global _DRIVER
    _LOCK.lock()
    try:
        if _DRIVER is not None:
            try:
                _DRIVER.stop()
            finally:
                _DRIVER = None
    finally:
        _LOCK.unlock()


def get_driver():
    return _DRIVER
