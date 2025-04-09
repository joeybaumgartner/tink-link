import uasyncio as asyncio
from pubsub import getPubSub, PubSub, Topics, Origin
from uart_async import BaseUart, HwUart


class ExtronSwVgaState:
    def __init__(self, profile: int = None, activeInput: int = 0):
        self.activeInput = activeInput
        self.profile = profile

    def clone(self):
        return ExtronSwVgaState(self.profile, self.activeInput)
    
    def __repr__(self):
        return f"ExtronSwVgaState(profile={self.profile},activeInput={self.activeInput})"


class Line:
    def __init__(self, line:str):
        self.line = line

    def is_error(self) -> bool:
        return self.find("E") == 0

    def get_error(self) -> int:
        if self.is_error():
            return int(self.line[1:3])
        else:
            return -1 # not en error

    def is_input(self) -> bool:
        return self.line.find("In") == 0 and (self.line.find("All") > 0 or self.line.find("Vid"))

    def get_input(self) -> int:
        if self.is_input():
            # Designed to work for lines with one input char eg "In3 All" or with two input chars eg "In10 All"
            return int(self.line[2:4])
        else:
            return -1 # not en error


class ExtronSwVga:
    def __init__(self, uart: BaseUart):
        self.state = ExtronSwVgaState()
        self.pubsub_origin = PubSub.create_origin("ExtronSwVga")
        self.uart = uart


    @classmethod
    def create_from_config(cls, config: dict):
        conn = config.get("connection", {})
        uart = HwUart(conn.get("uartId", 1), conn.get("txPin", 21), conn.get("rxPin", 20))
        extron = ExtronSwVga(uart)
        extron.start()
        return extron


    async def _on_message(self, payload: str, topic: str, origin: Origin):
        line = Line(payload)
        if line.is_input():
            input = line.get_input()
            self.state.activeInput = input
            print("Extron state change published: ", self.state)
            getPubSub().publish(Topics.SWITCHER_STATECHANGED, self.state.clone(), self.pubsub_origin)

    def start(self):
        self.uart.start()
        getPubSub().subscribe(Topics.UART_MESSAGE, self._on_message, self.pubsub_origin)
