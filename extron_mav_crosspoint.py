import uasyncio as asyncio
from pubsub import getPubSub, PubSub, Topics, Origin
from telnet import TelnetClient

class ExtronSwitcherState:
    def __init__(self, preset: int):
        self.preset = preset

    def clone(self):
        return ExtronSwitcherState(self.preset)
    
    def __repr__(self):
        return f"ExtronSwitcherState(preset={self.preset})"
    
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

    def is_preset(self) -> bool:
        return self.line.find("Rpr") == 0

    def get_input(self) -> int:
        if self.is_preset():
            # Designed to work for lines with one input char eg "In3 All" or with two input chars eg "In10 All"
            return int(self.line[3:5])
        else:
            return -1 # not en error
        
class ExtronMavCrosspoint:
    def __init__(self, telnetClient: TelnetClient):
        self.state = ExtronSwitcherState(0)
        self.pubsub_origin = PubSub.create_origin("ExtronMavCrosspoint")
        self.telnetClient = telnetClient

    async def _on_message(self, payload: str, topic: str, origin: Origin):
        line = Line(payload)
        if line.is_preset():
            preset = line.get_input()
            self.state.preset = preset
            print("Extron state change published: ", self.state)
            getPubSub().publish(Topics.SWITCHER_STATECHANGED, self.state.clone(), self.pubsub_origin)

    def subscribe(self):
        getPubSub().subscribe(Topics.TELNET_MESSAGE, self._on_message, self.pubsub_origin)