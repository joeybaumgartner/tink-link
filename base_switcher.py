from pubsub import getPubSub, PubSub, Topics, Origin

class ProfileMode:
    SVS = "SVS"
    REMOTE = "Remote"

    
class SwitcherTrigger:
    def __init__(self, key: str, mode: ProfileMode, profile: int, name: str):
        self.key = key
        self.mode = mode
        self.profile = profile
        self.name = name

    def clone(self):
        return SwitcherTrigger(self.key, self.mode, self.profile, self.name)
    
    def __repr__(self):
        return f"SwitcherTrigger(key={self.key},mode={self.mode},profile={self.profile},name={self.name})"
    

class BaseSwitcher:
    def __init__(self):
        self.triggers = []
    

    def addTrigger(self, trigger: SwitcherTrigger):
        found = self.findTrigger(trigger.key)
        if found != None:
            print(f"duplicate trigger found with key '{found.key}', replacing previous trigger with new one.")
            self.triggers.remove(found)
        self.triggers.append(trigger)


    def hasTrigger(self, key: str):
        return self.findTrigger(key) != None
    

    def removeTrigger(self, key: str):
        trigger = self.findTrigger(key)
        if trigger != None:
            self.triggers.remove(trigger)


    def findTrigger(self, key: str):
        for trigger in self.triggers:
            if trigger.key == key:
                return trigger
        return None
    

    async def Start(self):
        pass


    async def Stop(self):
        pass
