import uasyncio as asyncio
from pubsub import getPubSub, PubSub, Topics, Origin
from telnet import TelnetClient

class TelnetConnection:

    def __init__(self, hostname: str, port: int, username: str = "", password: str = "", init_string: str = ""):
        self.telnetClient = TelnetClient(hostname, port, username, password, init_string)
        self.pubsub_origin = PubSub.create_origin(f"telnet: {hostname}:{port}")
        self.is_open = False
        self._telnet_task = None

    def open(self):
        print("opening connection")
        # figure out how to do connection in here? maybe?

    def close(self):
        self.telnetClient.deinit()
        self.telnetClient = None

    def start(self):
        print("Starting telnet connection")

        if not self.is_open:
            self.open()
        self.run_task = True

        asyncio.wait_for(self.telnetClient.connect(), 10)

        if self._telnet_task is None or self._telnet_task.done():
            self._telnet_task = asyncio.create_task(self._read_telnet())

        # Determine which I need
        getPubSub().subscribe(Topics.REMOTE_MESSAGE, self._on_pubsub_message, self.pubsub_origin)
        getPubSub().subscribe(Topics.TCP_MESSAGE, self._on_pubsub_message, self.pubsub_origin)
        getPubSub().subscribe(Topics.TERMINAL_MESSAGE, self._on_pubsub_message, self.pubsub_origin)


    async def stop(self):
        self.run_task = False
        getPubSub().unsubscribe(Topics.REMOTE_MESSAGE, self._on_pubsub_message)
        getPubSub().unsubscribe(Topics.TCP_MESSAGE, self._on_pubsub_message)
        getPubSub().unsubscribe(Topics.TERMINAL_MESSAGE, self._on_pubsub_message)
        res = await self._telnet_task

    async def _read_telnet(self):

        while self.run_task:

            try:
                data = await self.telnetClient.readline()
                message = f"{data}\r\n"
            except OSError as e:
                await self.telnetClient.reconnect()
                message = "Reconnected"
            except Exception as e:
                message = f"Exception: {e}"
                
            getPubSub().publish(Topics.TELNET_MESSAGE, message, self.pubsub_origin)

            await asyncio.sleep_ms(50)
            
    async def _on_pubsub_message(self, payload: str, topic: str, origin: Origin):
        # copying what's in tcp-async for now
        prefix = self.pubsub.origin_name + ": "
        try:
            if(payload.find(prefix) == 0):
                message = payload[len(prefix):]
                self.telnetClient.write(message)
                print(f"tx: {origin.name} [{message.strip()}. rx {self.pubsub_origin.name}]")
        except Exception as e:
            print("Error writing to telnet: ", e)
