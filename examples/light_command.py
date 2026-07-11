# Set a Home Assistant light to 60% brightness over two seconds.
ha_bridge.commands.call_service(
    domain="light",
    service="turn_on",
    target={"entity_id": "light.shop"},
    service_data={
        "brightness_pct": 60,
        "transition": 2
    }
)
