from machine import Pin, UART
import uasyncio as asyncio
from pubsub import pubsub, PubSub, Topics, Origin



class Uart:

    def __init__(self, uart_id = 1, tx_pin = 21, rx_pin = 20, encoding = 'utf-8'):
        self.tx_pin = Pin(tx_pin, mode = Pin.OPEN_DRAIN)
        self.rx_pin = Pin(rx_pin, mode = Pin.IN)
        self.uart_id = uart_id
        self.uart = None
        self.pubsub_origin = PubSub.create_origin("uart" + str(self.uart_id))
        self.encoding = encoding
        self.is_open = False
        self._uart_task = None


    def open(self):
        if self.uart == None:
            self.uart = UART(self.uart_id)

        self.uart.init(9600, 8, None, 1,
            tx = self.tx_pin,
            rx = self.rx_pin,
            timeout = 100
        )
        self.is_open = True


    def close(self):
        self.is_open = False
        self.uart.deinit()
        self.uart = None
        
        
    def start(self):
        """
        Opens the uart if it's not already open and begins reading from it.
        Messages will be posted to the pubsub 
        """
        if not self.is_open:
            self.open()
        self.run_task = True

        if self._uart_task is None or self._uart_task.done():
            self._uart_task = asyncio.create_task(self._read_uart())

        pubsub.subscribe(Topics.REMOTE_MESSAGE, self._on_pubsub_message, self.pubsub_origin)
        pubsub.subscribe(Topics.TCP_MESSAGE, self._on_pubsub_message, self.pubsub_origin)
        pubsub.subscribe(Topics.TERMINAL_MESSAGE, self._on_pubsub_message, self.pubsub_origin)


    async def _read_uart(self):
        """
        Continuously read data from the UART.
        When data is received, decode and broadcast it without modification.
        (No "remote " helper is added for UART data.)
        """
        while self.run_task:
            if self.uart.any() > 0:
                data = self.uart.readline()
                if data:
                    try:
                        msg = data.decode(self.encoding).strip()
                        # Strip removes the trailing CR/LF, add it back
                        msg = msg + "\r\n"
                    except Exception:
                        msg = str(data)
                    print("UART received:", msg)
                    pubsub.publish(Topics.UART_MESSAGE, msg, self.pubsub_origin)
                    
            await asyncio.sleep_ms(50)


    async def _on_pubsub_message(self, payload: str, topic: str, origin: Origin):
        prefix = self.pubsub_origin.name + ":"
        try:
            if(payload.find(prefix) == 0):
                message = payload[len(prefix):]
                self.write(message)
                print(f"tx: {origin.name}: [{message.strip()}]. rx: {self.pubsub_origin.name}")
        except Exception as e:
            print("Error writing to UART:", e)
        

    def write(self, message):
        if(self.is_open):
            data = message.encode(self.encoding)
            self.uart.write(data)
            self.uart.flush()


    async def stop(self):
        """
        Requests the uart to end. 
        """
        self.run_task = False
        pubsub.unsubscribe(Topics.REMOTE_MESSAGE, self._on_pubsub_message)
        pubsub.unsubscribe(Topics.TCP_MESSAGE, self._on_pubsub_message)
        pubsub.unsubscribe(Topics.TERMINAL_MESSAGE, self._on_pubsub_message)
        res = await self._uart_task


