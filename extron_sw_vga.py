import uasyncio as asyncio
from pubsub import pubsub, PubSub, Topics, Origin
from typing import Callable, Dict, List, Any
from uart_async import BaseUart


class SwitcherState:
    def __init__(self, activeInput, activeOutput):
        self.activeInput = activeInput
        self.activeOutput = activeOutput

    def clone(self):
        return SwitcherState(self.activeInput, self.activeOutput)
    
    def __repr__(self):
        return f"SwitcherState(activeInput={self.activeInput}, activeOutput={self.activeOutput})"


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
        self.state = SwitcherState(None, 0)
        self.pubsub_origin = PubSub.create_origin("ExtronSwVga")
        self.uart = uart

    async def _on_message(self, payload: str, topic: str, origin: Origin):
        line = Line(payload)
        if line.is_input():
            input = line.get_input()
            self.state.activeInput = input
            print("Extron state change published: ", self.state)
            pubsub.publish(Topics.SWITCHER_STATECHANGED, self.state.clone(), self.pubsub_origin)

    def subscribe(self):
        pubsub.subscribe(Topics.UART_MESSAGE, self._on_message, self.pubsub_origin)
