import uasyncio as asyncio
from pubsub import getPubSub, PubSub, Topics, Origin
from uart_async import BaseUart, HwUart
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

    def is_input(self) -> bool:
        return self.line.find("In") == 0 and (self.line.find("All") > 0 or self.line.find("Vid"))

    def get_input(self) -> int:
        if self.is_input():
            # Designed to work for lines with one input char eg "In3 All" or with two input chars eg "In10 All"
            return int(self.line[2:4])
        else:
            return -1 # not en error


class ExtronSwVga(BaseSwitcher):
    def __init__(self, uart: BaseUart):
        super().__init__()
        self.pubsub_origin = PubSub.create_origin("ExtronSwVga")
        self.uart = uart


    @classmethod
    def create_from_config(cls, config: dict):
        conn = config.get("connection", {})
        uart = HwUart(conn.get("uartId", 1), conn.get("txPin", 21), conn.get("rxPin", 20))
        extron = ExtronSwVga(uart)
        triggers_conf = config.get("triggers", [])
        for trigger_conf in triggers_conf:
            if "input" not in trigger_conf or "mode" not in trigger_conf or "profile" not in trigger_conf:
                print("Malformed trigger conf for ExtronSwVga: ", trigger_conf)
                continue
            trig = SwitcherTrigger(
                str(trigger_conf.get("input")), trigger_conf.get("mode"), trigger_conf.get("profile"), trigger_conf.get("name", None)
            )
            extron.addTrigger(trig)
        return extron
    

    async def _on_message(self, payload: str, topic: str, origin: Origin):
        line = Line(payload)
        if line.is_input():
            input = line.get_input()
            trigger = self.findTrigger(str(input))
            if trigger != None:
                print("Extron trigger change published: ", trigger)
                getPubSub().publish(Topics.SWITCHER_TRIGGERCHANGED, trigger.clone(), self.pubsub_origin)
            else:
                print("extron input change detected but no matching trigger found")


    async def start(self):
        self.uart.start()
        getPubSub().subscribe(Topics.UART_MESSAGE, self._on_message, self.pubsub_origin)


    async def stop(self):
        self.uart.stop()
        getPubSub().unsubscribe(Topics.UART_MESSAGE, self._on_message)
