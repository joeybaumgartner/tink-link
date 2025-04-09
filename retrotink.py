from pubsub import getPubSub, PubSub, Topics, Origin
from uart_async import BaseUart, RmtUart
from base_switcher import SwitcherTrigger, ProfileMode


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
        uart = RmtUart(config.get("uartId", 0), config.get("txPin", 1), config.get("rxPin", 0))
        uart.start()
        tink = Retrotink(uart)
        tink.subscribe()
        return tink
    

    async def _on_switch_statechange(self, payload:SwitcherTrigger, topic, origin: Origin):
        print("Retrotink detected profile change")
        if(payload.mode == ProfileMode.SVS):
            msg = "SVS NEW INPUT=" + str(payload.profile)
            print("Switching profiles with command: ", msg)
            self.uart.writeLine(msg)
        elif(payload.mode == ProfileMode.REMOTE):
            msg = "remote prof" + str(payload.profile)
            print("Switching profiles with command: ", msg)
            self.uart.writeLine(msg)


    def subscribe(self):
        getPubSub().subscribe(Topics.SWITCHER_TRIGGERCHANGED, self._on_switch_statechange, self.pubsub_origin)
