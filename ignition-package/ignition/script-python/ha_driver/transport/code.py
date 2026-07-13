from java.lang import InterruptedException, Runnable, StringBuilder, Thread
from java.net import URI
from java.net.http import HttpClient, WebSocket
from java.util.concurrent import (
    CompletableFuture,
    ConcurrentHashMap,
    LinkedBlockingQueue
)
from java.util.concurrent.atomic import AtomicBoolean, AtomicInteger

from ha_driver.models import PendingRequest


class _Worker(Runnable):
    def __init__(self, target):
        self.target = target

    def run(self):
        self.target()


class _JavaWebSocketListener(WebSocket.Listener):
    """Java WebSocket callback listener for Home Assistant."""

    def __init__(self, transport):
        self.transport = transport
        self.logger = system.util.getLogger(
            "Ciprinet.HADriver.WebSocket"
        )
        self.buffer = StringBuilder()

    def onOpen(self, web_socket):
        self.logger.info("Home Assistant WebSocket opened")

        self.transport.socket = web_socket
        self.transport.connected.set(True)
        self.transport.reconnect_count = 0
        self.transport.listener.on_connected()

        # Request delivery of the first incoming message.
        web_socket.request(1)

    def onText(self, web_socket, data, last):
        try:
            self.buffer.append(str(data))

            if last:
                complete_message = self.buffer.toString()
                self.buffer.setLength(0)
                self.transport._on_raw_message(complete_message)

            # Request delivery of the next incoming message.
            web_socket.request(1)

        except Exception as error:
            message = (
                "Error processing Home Assistant message: %s"
                % error
            )
            self.logger.error(message)
            self.transport.listener.on_transport_error(message)

        return CompletableFuture.completedFuture(None)

    def onError(self, web_socket, error):
        message = str(error)
        self.logger.error(
            "Home Assistant WebSocket error: %s" % message
        )

        self.transport.socket = None
        self.transport.connected.set(False)
        self.transport.authenticated.set(False)
        self.transport.listener.on_transport_error(message)
        self.transport._schedule_reconnect()

    def onClose(self, web_socket, status_code, reason):
        self.logger.warn(
            "Home Assistant WebSocket closed: %s %s"
            % (status_code, reason)
        )

        self.transport.socket = None
        self.transport.connected.set(False)
        self.transport.authenticated.set(False)
        self.transport.listener.on_disconnected(str(reason))
        self.transport._schedule_reconnect()

        return CompletableFuture.completedFuture(None)


class HomeAssistantTransport(object):
    def __init__(self, config, listener):
        self.config = config
        self.listener = listener
        self.logger = system.util.getLogger("ha_driver.transport")
        self.request_ids = AtomicInteger(0)
        self.pending = ConcurrentHashMap()
        self.outbound = LinkedBlockingQueue()
        self.running = AtomicBoolean(False)
        self.connected = AtomicBoolean(False)
        self.authenticated = AtomicBoolean(False)
        self.reconnect_scheduled = AtomicBoolean(False)
        self.socket = None
        self.sender_thread = None
        self.maintenance_thread = None
        self.reconnect_count = 0

    def start(self):
        if not self.running.compareAndSet(False, True):
            return

        self._start_workers()
        self._connect()

    def stop(self):
        self.running.set(False)
        self.reconnect_scheduled.set(False)

        web_socket = self.socket
        self.socket = None

        if web_socket is not None:
            try:
                web_socket.sendClose(
                    WebSocket.NORMAL_CLOSURE,
                    "Ignition Home Assistant driver stopping"
                )
            except Exception as exc:
                self.logger.warn(
                    "Error while closing Home Assistant WebSocket: %s"
                    % exc
                )

        if self.sender_thread is not None:
            self.sender_thread.interrupt()

        if self.maintenance_thread is not None:
            self.maintenance_thread.interrupt()

        self.connected.set(False)
        self.authenticated.set(False)

    def send_request(
        self,
        message,
        callback=None,
        timeout_ms=None,
        context=None
    ):
        request_id = self.request_ids.incrementAndGet()
        message = dict(message)
        message["id"] = request_id
        now = system.date.toMillis(system.date.now())

        pending = PendingRequest(
            request_id,
            message.get("type", "unknown"),
            now,
            timeout_ms or self.config.get(
                "request_timeout_ms",
                10000
            ),
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
        if not self.running.get():
            return

        self.reconnect_scheduled.set(False)
        self.listener.on_transport_state("CONNECTING")

        try:
            self.logger.info(
                "Connecting to Home Assistant at %s"
                % self.config["url"]
            )

            client = HttpClient.newHttpClient()
            listener = _JavaWebSocketListener(self)

            future = (
                client
                .newWebSocketBuilder()
                .buildAsync(
                    URI.create(self.config["url"]),
                    listener
                )
            )

            # Join exposes HTTP upgrade failures such as 403 responses.
            web_socket = future.join()
            self.socket = web_socket

            self.logger.info(
                "Home Assistant WebSocket client started"
            )

        except Exception as exc:
            message = "Unable to connect WebSocket: %s" % exc
            self.logger.error(message)
            self.listener.on_transport_error(message)
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
            self.listener.on_transport_error(
                "Message handling failed: %s" % exc
            )

    def _start_workers(self):
        self.sender_thread = Thread(
            _Worker(self._sender_loop),
            "ha-driver-sender"
        )
        self.sender_thread.setDaemon(True)
        self.sender_thread.start()

        self.maintenance_thread = Thread(
            _Worker(self._maintenance_loop),
            "ha-driver-maintenance"
        )
        self.maintenance_thread.setDaemon(True)
        self.maintenance_thread.start()

    def _sender_loop(self):
        while self.running.get():
            try:
                message = self.outbound.take()

                if not self.connected.get() or self.socket is None:
                    self.outbound.put(message)
                    Thread.sleep(250)
                    continue

                raw = system.util.jsonEncode(message)
                self.socket.sendText(raw, True)
                self.listener.on_message_sent()

            except InterruptedException:
                return
            except Exception as exc:
                self.listener.on_transport_error(
                    "Send failed: %s" % exc
                )
                Thread.sleep(500)

    def _maintenance_loop(self):
        while self.running.get():
            try:
                now = system.date.toMillis(system.date.now())
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
                Thread.sleep(1000)

            except InterruptedException:
                return
            except Exception as exc:
                self.listener.on_transport_error(
                    "Maintenance failed: %s" % exc
                )
                Thread.sleep(1000)

    def _schedule_reconnect(self):
        if not self.running.get():
            return

        if not self.reconnect_scheduled.compareAndSet(False, True):
            return

        self.reconnect_count += 1
        initial = self.config.get("reconnect_initial_ms", 1000)
        maximum = self.config.get("reconnect_max_ms", 60000)
        multiplier = self.config.get("reconnect_multiplier", 2.0)
        delay = min(
            maximum,
            int(initial * (multiplier ** (self.reconnect_count - 1)))
        )

        self.listener.on_reconnect_wait(delay, self.reconnect_count)
        self.logger.info("Reconnect scheduled in %s ms" % delay)

        def reconnect():
            try:
                Thread.sleep(delay)
                if self.running.get():
                    self._connect()
            except InterruptedException:
                return

        thread = Thread(
            _Worker(reconnect),
            "ha-driver-reconnect"
        )
        thread.setDaemon(True)
        thread.start()
