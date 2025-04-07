import uasyncio as asyncio
from pubsub import getPubSub, PubSub, Topics, Origin
from telnet import TelnetClient

# Global sets for shared chat room clients
chat_clients_serial_over_tcp = set()      # serial_over_tcp client writer objects

pubsub_tcp_origin = PubSub.create_origin("tcp")

class TelnetConnection:

    def __init__(self, hostname: str, port: int, username: str = "", password: str = "", init_string: str = ""):
        self.telnetClient = TelnetClient(hostname, port, username, password, init_string)
        self.pubsub_origin = PubSub.create_origin(f"telnet: {hostname}:{port}")
        self.is_open = False
        self._telnet_task = None

    def close(self):
        self.telnetClient.deinit()
        self.telnetClient = None

    async def start(self):

        await self.telnetClient.connect()

        if self.telnetClient.connected:
            print("Telnet client connected")
            self.run_task = True
        else:
            print("Could not connect")

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
            except Exception as e:
                message = f"Exception: {e}"
                
            getPubSub().publish(Topics.TELNET_MESSAGE, message, self.pubsub_origin)

            await asyncio.sleep_ms(50)
            
    async def _on_pubsub_message(self, payload: str, topic: str, origin: Origin):
        # Send to serial_over_tcp clients:
        for writer in list(chat_clients_serial_over_tcp):
            try:
                writer.write(payload.encode('utf-8'))
                await writer.drain()
            except Exception as e:
                print("Error broadcasting to raw_tcp client:", e)
        clean_message = payload.strip()
        print(f"tx: {origin.name}: [{clean_message}]. rx: {pubsub_tcp_origin.name}")
