from typing import Callable, Dict, List, Any
import asyncio

class Topics:
    UART_MESSAGE = "/uart/message"      # payload: str
    TCP_MESSAGE = "/tcp/message"        # payload: str
    WS_MESSAGE = "/ws/message"          # payload: str
    TERMINAL_MESSAGE = "/terminal/message"    # payload: str


class Origin:
    def __init__(self, name: str = None):
        self.name = name

    def __repr__(self):
        return f"Origin(name={self.name!r})"

class PubSub:
    def __init__(self):
        self._subscriptions = {}
        self._queue = asyncio.Queue()
        self._processing_task = None

    @classmethod
    def create_origin(cls, name: str = None) -> Origin:
        """Create an origin identifier. Uses an object with a name property."""
        return Origin(name)

    def subscribe(self, topic: str, callback: Callable[[Any, str, Any], None], origin: Any = None) -> None:
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

    def unsubscribe(self, topic: str, callback: Callable[[Any, str, Any], None]) -> None:
        """Unsubscribe a callback from a topic."""
        if topic in self._subscriptions:
            self._subscriptions[topic] = [
                sub for sub in self._subscriptions[topic] if sub["callback"] != callback
            ]
            if not self._subscriptions[topic]:
                del self._subscriptions[topic]

    def publish(self, topic: str, payload: Any, origin: Any = None) -> None:
        """Publish a message asynchronously, ensuring sequential processing."""
        if topic in self._subscriptions:
            for sub in self._subscriptions[topic]:
                sub_origin = sub["origin"]
                if sub_origin is None or (sub_origin is not origin and sub_origin != origin):
                    self._queue.put_nowait(sub["callback"](payload, topic, origin))
        
        # Start queue processing if not already running
        if self._processing_task is None or self._processing_task.done():
            self._processing_task = asyncio.create_task(self._process_queue())

    async def _process_queue(self) -> None:
        """Process the queued tasks sequentially."""
        while not self._queue.empty():
            # Get the next task
            task = await self._queue.get()  
            # Check if it's an async function
            if asyncio.iscoroutine(task):  
                await task
            else:
                task()


# Create a shared instance of PubSub
pubsub = PubSub()