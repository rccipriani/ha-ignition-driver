# Run in Gateway scope.

# Turn on a Home Assistant input_boolean.
command_id = ha_bridge.commands.call_service(
    domain="input_boolean",
    service="turn_on",
    target={"entity_id": "input_boolean.ignition_test"}
)

system.util.getLogger("ha_bridge.example").info(
    "Submitted command %s" % command_id
)
