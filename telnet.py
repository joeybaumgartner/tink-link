try:
    import uasyncio as asyncio
except:
    import asyncio

class TelnetClient:

    def __init__(self, hostname: str, port: int = 23, username: str = "", password: str = "", init_string: str = ""):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.init_string = init_string
        self.encoding = 'utf-8'
        self.reader = None
        self.writer = None
        self.connected = False
        self.initialized = False

    async def connect(self):
        try:
            print(f"Trying to connect to telnet: {self.hostname}:{self.port}")
            self.reader, self.writer = await asyncio.open_connection(self.hostname, self.port)
            self.connected = True
        except OSError as oe:
            raise ValueError(f"OS Connection Error {oe}")
        except Exception as e:
            raise ValueError(f"General Error on Connect {oe}")
        
    async def init(self):
        # Attempt to read back banner from connecting.
        # We don't do anything with this, but we need it out of
        # the stream.
        data = await self.reader.read(200)

        if self.password != "":
            print("Attempting to login")
            self.writer.write(f"{self.password}\r\n".encode())
            text = await self.reader.readline()
            print("text output: " , text.decode(self.encoding).strip())

        if self.init_string != "":
            h = bytes(f"{self.init_string}\r\n", self.encoding)
            self.writer.write(h)
            data = await self.reader.readline()
            data = data.decode(self.encoding).strip()
            print(f"Init response: {data}")

        self.initialized = True


    async def reconnect(self) -> str:
        await self.connect()
        await self.init()

    async def readline(self) -> str:
        if not self.connected:
            await self.connect()

        if not self.initialized:
            await self.init()

        data = await self.reader.readline()
        r = data.decode(self.encoding).strip()
        
        return r
    
    async def write(self, message: str):
        message = message + "\r\n"   # <- function should be named writeline
        if self.connected:
            data = bytes(message, self.encoding)
            self.writer.write(data)
            self.writer.drain()

    async def close(self):
        if self.writer:
            await self.writer.drain()
            self.writer.close()
            await self.writer.wait_closed()