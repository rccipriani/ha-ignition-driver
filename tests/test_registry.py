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
registry = load("registry")


def test_split_entity_id():
    assert registry.split_entity_id("sensor.temperature") == ["sensor", "temperature"]


def test_stable_mapping():
    reg = registry.EntityRegistry("[default]HomeAssistant")
    first = reg.mapping_for("sensor.garage_temperature")
    second = reg.mapping_for("sensor.garage_temperature")
    assert first is second
    assert first.tag_path.endswith("/Entities/sensor/garage_temperature")


def test_domain_filtering():
    reg = registry.EntityRegistry(
        "[default]HomeAssistant",
        exclude_domains=["automation"]
    )
    assert reg.should_include("sensor.temperature")
    assert not reg.should_include("automation.test")
