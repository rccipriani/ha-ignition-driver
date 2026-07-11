import importlib.util
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ignition" / "project_library" / "ha_bridge"

ha_bridge = types.ModuleType("ha_bridge")
ha_bridge.__path__ = [str(PACKAGE)]
sys.modules["ha_bridge"] = ha_bridge


def load(name):
    spec = importlib.util.spec_from_file_location("ha_bridge." + name, PACKAGE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules["ha_bridge." + name] = module
    spec.loader.exec_module(module)
    return module


load("models")
protocol = load("protocol")


def test_call_service_message():
    message = protocol.call_service(
        "light",
        "turn_on",
        {"brightness_pct": 50},
        {"entity_id": "light.shop"}
    )
    assert message["type"] == "call_service"
    assert message["domain"] == "light"
    assert message["service"] == "turn_on"
    assert message["target"]["entity_id"] == "light.shop"


def test_parse_entity_state():
    state = protocol.parse_entity_state({
        "entity_id": "sensor.test",
        "state": "12.5",
        "attributes": {"unit_of_measurement": "C"}
    })
    assert state.entity_id == "sensor.test"
    assert state.state == "12.5"
