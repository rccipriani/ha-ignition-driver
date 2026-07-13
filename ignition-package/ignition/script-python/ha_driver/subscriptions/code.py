class SubscriptionManager(object):
    def __init__(self):
        self.handlers = {}

    def register(self, subscription_id, handler):
        self.handlers[int(subscription_id)] = handler

    def unregister(self, subscription_id):
        self.handlers.pop(int(subscription_id), None)

    def handle(self, message):
        subscription_id = message.get("id")
        handler = self.handlers.get(subscription_id)
        if handler:
            handler(message)
            return True
        return False
