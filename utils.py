import json

CONFIG_FILE = 'config.json'

class Utils:

    def __init__(self):
        self._config = None

    def get_config(self, filename: str = CONFIG_FILE) -> dict:
        if self._config != None:
            return self._config
        try:
            with open(filename) as f:
                self._config = json.load(f)
                return self._config
        except OSError:
            print("No config found")
            return None
        
    def write_config(self, data: dict, filename: str = CONFIG_FILE):
        try:
            with open(filename, 'w') as file:
                file.write(json.dumps(data))
        except OSError as oe:
            print(f"Could not write config file {oe}")
            pass