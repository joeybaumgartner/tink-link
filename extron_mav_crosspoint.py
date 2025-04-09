import uasyncio as asyncio
from pubsub import getPubSub, PubSub, Topics, Origin
from telnet import TelnetClient
import telnet_async

class ExtronMavCpState:
    def __init__(self, profile: int = None, preset: int = 0):
        self.preset = preset
        self.profile = profile

    def clone(self):
        return ExtronMavCpState(self.profile, self.preset)
    
    def __repr__(self):
        return f"ExtronMavCpState(profile={self.profile},preset={self.preset})"
    
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

    def get_preset(self) -> int:
        if self.is_preset():
            # Designed to work for lines that end as RprXX
            return int(self.line[3:5])
        else:
            return -1 # not en error
        
class ExtronMavCp:
    def __init__(self, telnetClient: TelnetClient):
        self.state = ExtronMavCpState()
        self.pubsub_origin = PubSub.create_origin("ExtronMavCp")
        self.telnetClient = telnetClient


    @classmethod
    def create_from_config(cls, config: dict):    
        conn = config.get("connection", {})
        telnet = telnet_async.TelnetConnection(
            config.get("hostname"), config.get("port"), config.get("username", ""), config.get("password", ""), config.get("init_string", "")
        )
        extroncp = ExtronMavCp(telnet)
        extroncp.start()
        return extroncp
    

    async def _on_message(self, payload: str, topic: str, origin: Origin):
        line = Line(payload)
        if line.is_preset():
            preset = line.get_preset()
            self.state.preset = preset
            print("Extron state change published: ", self.state)
            getPubSub().publish(Topics.SWITCHER_STATECHANGED, self.state.clone(), self.pubsub_origin)


    def start(self):
        self.telnetClient.start()
        getPubSub().subscribe(Topics.TELNET_MESSAGE, self._on_message, self.pubsub_origin)