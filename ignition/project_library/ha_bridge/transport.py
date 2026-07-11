from java.net import URI
from java.util.concurrent import ConcurrentHashMap, LinkedBlockingQueue
from java.util.concurrent.atomic import AtomicBoolean, AtomicInteger
from java.lang import Runnable, Thread

from ha_bridge.models import PendingRequest


class _Worker(Runnable):
    def __init__(self, target):
        self.target = target

    def run(self):
        self.target()


class HomeAssistantTransport(object):
    def __init__(self, config, listener):
        self.config = config
        self.listener = listener
        self.logger = system.util.getLogger("ha_bridge.transport")
        self.request_ids = AtomicInteger(0)
        self.pending = ConcurrentHashMap()
        self.outbound = LinkedBlockingQueue()
        self.running = AtomicBoolean(False)
        self.connected = AtomicBoolean(False)
        self.authenticated = AtomicBoolean(False)
        self.socket = None
        self.sender_thread = None
        self.maintenance_thread = None
        self.reconnect_count = 0

    def start(self):
        if self.running.compareAndSet(False, True):
            self._start_workers()
            self._connect()

    def stop(self):
        self.running.set(False)
        try:
            if self.socket:
                self.socket.close()
        except Exception:
            self.logger.warn("Error while closing Home Assistant WebSocket")
        self.socket = None
        self.connected.set(False)
        self.authenticated.set(False)

    def send_request(self, message, callback=None, timeout_ms=None, context=None):
        request_id = self.request_ids.incrementAndGet()
        message = dict(message)
        message["id"] = request_id
        now = system.date.toMillis(system.date.now())
        pending = PendingRequest(
            request_id,
            message.get("type", "unknown"),
            now,
            timeout_ms or self.config.get("request_timeout_ms", 10000),
            callback,
            context
        )
        self.pending.put(request_id, pending)
        self.outbound.put(message)
        self.listener.on_pending_count(self.pending.size())
        return request_id

    def send_message(self, message):
        self.outbound.put(dict(message))

    def _connect(self):
        self.listener.on_transport_state("CONNECTING")
        transport = self

        try:
            from org.java_websocket.client import WebSocketClient

            class Client(WebSocketClient):
                def onOpen(self, handshake):
                    transport.connected.set(True)
                    transport.listener.on_connected()

                def onMessage(self, raw):
                    transport._on_raw_message(raw)

                def onClose(self, code, reason, remote):
                    transport.connected.set(False)
                    transport.authenticated.set(False)
                    transport.listener.on_disconnected(reason)
                    transport._schedule_reconnect()

                def onError(self, error):
                    transport.listener.on_transport_error(str(error))

            self.socket = Client(URI(self.config["url"]))
            self.socket.connect()
        except Exception as exc:
            self.listener.on_transport_error(
                "Unable to create WebSocket client: %s" % exc
            )
            self._schedule_reconnect()

    def _on_raw_message(self, raw):
        try:
            message = system.util.jsonDecode(raw)
            self.listener.on_message_received()
            message_type = message.get("type")

            if message_type == "auth_required":
                self.listener.on_transport_state("AUTHENTICATING")
                self.send_message({
                    "type": "auth",
                    "access_token": self.config["access_token"]
                })
                return

            if message_type == "auth_ok":
                self.authenticated.set(True)
                self.listener.on_authenticated(message)
                return

            if message_type == "auth_invalid":
                self.authenticated.set(False)
                self.listener.on_auth_invalid(message)
                return

            if message_type == "result":
                pending = self.pending.remove(message.get("id"))
                self.listener.on_pending_count(self.pending.size())
                if pending and pending.callback:
                    pending.callback(message, pending)
                self.listener.on_result(message, pending)
                return

            if message_type == "event":
                self.listener.on_event(message)
                return

            self.listener.on_unhandled_message(message)
        except Exception as exc:
            self.listener.on_transport_error("Message handling failed: %s" % exc)

    def _start_workers(self):
        self.sender_thread = Thread(_Worker(self._sender_loop), "ha-bridge-sender")
        self.sender_thread.setDaemon(True)
        self.sender_thread.start()

        self.maintenance_thread = Thread(
            _Worker(self._maintenance_loop),
            "ha-bridge-maintenance"
        )
        self.maintenance_thread.setDaemon(True)
        self.maintenance_thread.start()

    def _sender_loop(self):
        while self.running.get():
            try:
                message = self.outbound.take()
                if not self.connected.get() or not self.socket:
                    self.outbound.put(message)
                    Thread.sleep(250)
                    continue
                raw = system.util.jsonEncode(message)
                self.socket.send(raw)
                self.listener.on_message_sent()
            except InterruptedException:
                return
            except Exception as exc:
                self.listener.on_transport_error("Send failed: %s" % exc)
                Thread.sleep(500)

    def _maintenance_loop(self):
        while self.running.get():
            now = system.date.toMillis(system.date.now())
            try:
                iterator = self.pending.entrySet().iterator()
                expired = []
                while iterator.hasNext():
                    entry = iterator.next()
                    pending = entry.getValue()
                    if pending.is_expired(now):
                        expired.append(entry.getKey())

                for request_id in expired:
                    pending = self.pending.remove(request_id)
                    if pending:
                        self.listener.on_request_timeout(pending)
                self.listener.on_pending_count(self.pending.size())
            except Exception as exc:
                self.listener.on_transport_error("Maintenance failed: %s" % exc)
            Thread.sleep(1000)

    def _schedule_reconnect(self):
        if not self.running.get():
            return

        self.reconnect_count += 1
        delay = self.config.get("reconnect_initial_ms", 1000)
        maximum = self.config.get("reconnect_max_ms", 60000)
        multiplier = self.config.get("reconnect_multiplier", 2.0)
        delay = min(maximum, int(delay * (multiplier ** (self.reconnect_count - 1))))
        self.listener.on_reconnect_wait(delay, self.reconnect_count)

        def reconnect():
            Thread.sleep(delay)
            if self.running.get():
                self._connect()

        thread = Thread(_Worker(reconnect), "ha-bridge-reconnect")
        thread.setDaemon(True)
        thread.start()
