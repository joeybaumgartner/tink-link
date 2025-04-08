import uasyncio as asyncio
from async_queue import AsyncQueue

class Topics:
    UART_MESSAGE = "/uart/message"                      # payload: str
    TCP_MESSAGE = "/tcp/message"                        # payload: str
    REMOTE_MESSAGE = "/remote/message"                  # payload: str
    TERMINAL_MESSAGE = "/terminal/message"              # payload: str
    SWITCHER_STATECHANGED = "/switcher/stateChanged"    # payload: SwitcherState
    TELNET_MESSAGE = "/telnet/message"                  # payload: str



class Origin:
    def __init__(self, name: str = None):
        self.name = name

    def __repr__(self):
        return f"Origin(name={self.name!r})"
    
async def _g():
    pass

type_coro = type(_g())

class PubSub:
    def __init__(self):
        self._subscriptions = {}
        self._queue = AsyncQueue()
        self._processing_task = None


    @classmethod
    def create_origin(cls, name: str = None) -> Origin:
        """Create an origin identifier. Uses an object with a name property."""
        return Origin(name)


    def subscribe(self, topic: str, callback, origin = None) -> None:
        """
        Subscribe to a topic with a callback and optional origin.
        
        :param topics: The topic to subscribe to. Topics and their payload types are in the Topics enum
        :param callback: The callback to call when topic is published to. Should have the form on_topic(payload: Any)
        :param origin: Optional argument to differentiate the subscriber from the publisher. 
        Could be from create_origin or self in OO code.
        """
        if topic not in self._subscriptions:
            self._subscriptions[topic] = []
        self._subscriptions[topic].append({"callback": callback, "origin": origin})


    def unsubscribe(self, topic: str, callback) -> None:
        """
        Unsubscribe the specified callback from the specified topic. Must be called with the exact topic string used for subscribe, including any wildcard 
        characters. Wildcard's do not result in unsubscribing multiple matching subscriptions.
        """
        if topic in self._subscriptions:
            self._subscriptions[topic] = [
                sub for sub in self._subscriptions[topic] if sub["callback"] != callback
            ]
            if not self._subscriptions[topic]:
                del self._subscriptions[topic]


    def _match_subsc_topic(self, pattern, topic):
        pattern_parts = pattern.strip("/").split("/")
        path_parts = topic.strip("/").split("/")

        for i in range(len(pattern_parts)):
            if i >= len(path_parts):
                return False

            if pattern_parts[i] == "*":
                if i == len(pattern_parts) - 1:
                    # Last pattern segment is "*", match remaining path segments
                    return True
                # Else just match this segment and continue
            elif pattern_parts[i] != path_parts[i]:
                return False

            i += 1

        return i == len(path_parts)
    

    def match_subscriptions(self, topic):
        ret_vals = []
        for subsc_topic in self._subscriptions:
            if self._match_subsc_topic(subsc_topic, topic):
                ret_vals.append(subsc_topic)
        return ret_vals


    def publish(self, topic: str, payload, origin = None) -> None:
        """Publish a message asynchronously, ensuring sequential processing."""
        matches = self.match_subscriptions(topic)
        for match in matches:
            for sub in self._subscriptions[match]:
                sub_origin = sub["origin"]
                if sub_origin is None or (sub_origin is not origin and sub_origin != origin):
                    self._queue.put_nowait((sub["callback"], payload, topic, origin))
        
        # Start queue processing if not already running
        if self._processing_task is None or self._processing_task.done():
            self._processing_task = asyncio.create_task(self._process_queue())


    async def _process_queue(self) -> None:
        """Process the queued tasks sequentially."""
        while not self._queue.empty():
            # Get the next task
            callback, payload, topic, origin = await self._queue.get()
            res = self._run_callback(callback,(payload, topic, origin))


    def _run_callback(self, func, tup_args):
        res = func(*tup_args)
        # Check if it's an async function
        if isinstance(res, type_coro):
            res = asyncio.create_task(res)
        return res


_pubsub = None

# Get a shared instance of PubSub
def getPubSub():
    global _pubsub
    if _pubsub == None:
        _pubsub = PubSub()
    return _pubsub