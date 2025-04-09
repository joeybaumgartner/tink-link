from pubsub import getPubSub, PubSub, Topics, Origin
from uart_async import BaseUart
from extron_mav_crosspoint import ExtronMavCpState
from extron_sw_vga import ExtronSwVgaState
from uart_async import RmtUart


class RetrotinkState:
    def __init__(self, power = False, profile = 0):
        self.power = power
        self.profile = profile

    def clone(self):
        return RetrotinkState(self.clone, self.profile_num)
    
    def __repr__(self):
        return f"RetrotinkState(power={self.power}, profile_num={self.profile})"


class Retrotink:
    def __init__(self, uart: BaseUart):
        self.pubsub_origin = PubSub.create_origin("Retrotink")
        self.uart = uart


    @classmethod
    def create_from_config(cls, config: dict):
        print("constructing RmtUart with config: ", config)
        uart = RmtUart(config.get("uartId", 0), config.get("txPin", 1), config.get("rxPin", 0))
        uart.start()
        tink = Retrotink(uart)
        tink.subscribe()
        return tink
    

    async def _on_switch_statechange(self, payload, topic, origin: Origin):
        print("in tink switch statechange")


    def subscribe(self):
        getPubSub().subscribe(Topics.SWITCHER_STATECHANGED, self._on_switch_statechange, self.pubsub_origin)
