from ha_bridge import protocol
from ha_bridge.registry import EntityRegistry
from ha_bridge.subscriptions import SubscriptionManager
from ha_bridge.tags import TagManager
from ha_bridge.transport import HomeAssistantTransport


class HomeAssistantDriver(object):
    def __init__(self, config):
        self.config = config
        self.logger = system.util.getLogger("ha_bridge.driver")
        self.tags = TagManager(config["tag_root"])
        self.registry = EntityRegistry(
            config["tag_root"],
            config.get("include_domains"),
            config.get("exclude_domains")
        )
        self.subscriptions = SubscriptionManager()
        self.transport = HomeAssistantTransport(config, self)
        self.state_subscription_id = None
        self.received_messages = 0
        self.sent_messages = 0

    def start(self):
        self.tags.ensure_driver_tags()
        self.tags.write_driver_many({
            "Enabled": True,
            "ConnectionState": "STARTING",
            "LastError": ""
        })
        self.transport.start()

    def stop(self):
        self.tags.write_driver("ConnectionState", "STOPPING")
        self.transport.stop()
        self.tags.write_driver_many({
            "Connected": False,
            "Authenticated": False,
            "ConnectionState": "STOPPED"
        })

    def on_transport_state(self, state):
        self.tags.write_driver("ConnectionState", state)

    def on_connected(self):
        self.tags.write_driver_many({
            "Connected": True,
            "LastConnected": system.date.now(),
            "ConnectionState": "AUTHENTICATING",
            "LastError": ""
        })

    def on_disconnected(self, reason):
        self.tags.write_driver_many({
            "Connected": False,
            "Authenticated": False,
            "ConnectionState": "DISCONNECTED",
            "LastError": reason or "WebSocket disconnected"
        })

    def on_authenticated(self, message):
        self.tags.write_driver_many({
            "Authenticated": True,
            "ConnectionState": "INITIALIZING"
        })
        self.transport.send_request(protocol.get_states(), self._on_get_states)

    def on_auth_invalid(self, message):
        self.tags.write_driver_many({
            "Authenticated": False,
            "ConnectionState": "FAULTED",
            "LastError": message.get("message", "Home Assistant authentication failed")
        })

    def _on_get_states(self, message, pending):
        if not message.get("success"):
            self.on_transport_error("get_states failed: %s" % message.get("error"))
            return

        raw_states = message.get("result") or []
        states = []
        for raw in raw_states:
            state = protocol.parse_entity_state(raw)
            if state and self.registry.should_include(state.entity_id):
                states.append(state)

        self.registry.reconcile_states(states)
        for state in states:
            mapping = self.registry.mapping_for(state.entity_id)
            self.tags.ensure_entity(mapping, state)
            self.tags.write_entity_state(mapping, state)

        self.tags.write_driver_many({
            "EntityCount": self.registry.count(),
            "LastStateSync": system.date.now(),
            "ConnectionState": "SUBSCRIBING"
        })

        self.state_subscription_id = self.transport.send_request(
            protocol.subscribe_events("state_changed"),
            self._on_subscribed
        )

    def _on_subscribed(self, message, pending):
        if not message.get("success"):
            self.on_transport_error("state_changed subscription failed")
            return
        self.subscriptions.register(
            self.state_subscription_id,
            self._handle_state_changed
        )
        self.tags.write_driver("ConnectionState", "ONLINE")

    def _handle_state_changed(self, message):
        event = message.get("event") or {}
        data = event.get("data") or {}
        new_state = protocol.parse_entity_state(data.get("new_state"))
        if not new_state or not self.registry.should_include(new_state.entity_id):
            return

        mapping = self.registry.mapping_for(new_state.entity_id)
        self.tags.ensure_entity(mapping, new_state)
        self.tags.write_entity_state(mapping, new_state)
        self.tags.write_driver("EntityCount", self.registry.count())

    def on_event(self, message):
        if not self.subscriptions.handle(message):
            self.logger.debug("Unhandled subscription event: %s" % message)

    def on_result(self, message, pending):
        if pending and pending.command_type == "call_service":
            if message.get("success"):
                self.logger.info(
                    "Home Assistant command accepted: %s" % pending.context
                )
            else:
                self.logger.warn(
                    "Home Assistant command failed: %s" % message.get("error")
                )

    def on_unhandled_message(self, message):
        self.logger.debug("Unhandled Home Assistant message: %s" % message)

    def on_transport_error(self, error):
        self.logger.error(error)
        self.tags.write_driver("LastError", error)

    def on_message_received(self):
        self.received_messages += 1
        self.tags.write_driver_many({
            "ReceivedMessages": self.received_messages,
            "LastMessage": system.date.now()
        })

    def on_message_sent(self):
        self.sent_messages += 1
        self.tags.write_driver("SentMessages", self.sent_messages)

    def on_pending_count(self, count):
        self.tags.write_driver("PendingRequests", count)

    def on_request_timeout(self, pending):
        self.on_transport_error(
            "Request %s (%s) timed out" % (
                pending.request_id,
                pending.command_type
            )
        )

    def on_reconnect_wait(self, delay_ms, reconnect_count):
        self.tags.write_driver_many({
            "ConnectionState": "RECONNECT_WAIT",
            "ReconnectCount": reconnect_count,
            "LastError": "Reconnect scheduled in %s ms" % delay_ms
        })
