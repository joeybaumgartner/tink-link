import uasyncio as asyncio
from pubsub import getPubSub, PubSub, Topics, Origin
from telnet import TelnetClient
import telnet_async
from base_switcher import BaseSwitcher, SwitcherTrigger


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
        


class ExtronMavCp(BaseSwitcher):
    def __init__(self, telnetClient: TelnetClient):
        super().__init__()
        self.pubsub_origin = PubSub.create_origin("ExtronMavCp")
        self.telnetClient = telnetClient


    @classmethod
    def create_from_config(cls, config: dict):    
        conn = config.get("connection", {})
        telnet = telnet_async.TelnetConnection(
            conn.get("hostname"), conn.get("port"), conn.get("username", ""), conn.get("password", ""), conn.get("init_string", "")
        )
        extron = ExtronMavCp(telnet)
        triggers_conf = config.get("triggers", [])
        for trigger_conf in triggers_conf:
            if "preset" not in trigger_conf or "mode" not in trigger_conf or "profile" not in trigger_conf:
                print("Malformed trigger conf for ExtronMavCp: ", trigger_conf)
                continue
            trig = SwitcherTrigger(
                str(trigger_conf.get("preset")), trigger_conf.get("mode"), trigger_conf.get("profile"), trigger_conf.get("name", None)
            )
            extron.addTrigger(trig)
        return extron
    

    async def _on_message(self, payload: str, topic: str, origin: Origin):
        line = Line(payload)
        if line.is_preset():
            preset = line.get_preset()
            trigger = self.findTrigger(str(preset))
            print("Extron trigger change published: ", trigger)
            getPubSub().publish(Topics.SWITCHER_TRIGGERCHANGED, trigger.clone(), self.pubsub_origin)


    async def start(self):
        await self.telnetClient.start()
        getPubSub().subscribe(Topics.TELNET_MESSAGE, self._on_message, self.pubsub_origin)


    async def stop(self):
        await self.telnetClient.stop()
        getPubSub().unsubscribe(Topics.TELNET_MESSAGE, self._on_message)