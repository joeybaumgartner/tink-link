from machine import Pin, UART
import uasyncio as asyncio
from pubsub import pubsub, PubSub, Topics, Origin
from esp32 import RMT
import time
import math
import micropython

DEFAULT_BAUD = 9600

class BaseUart:
    def __init__(self, uart_id = 1, tx_pin = 21, rx_pin = 20, encoding = 'utf-8', baud = DEFAULT_BAUD):
        self.tx_pin = Pin(tx_pin, mode = Pin.OUT)
        self.rx_pin = Pin(rx_pin, mode = Pin.IN)
        self.uart_id = uart_id
        self.pubsub_origin = PubSub.create_origin("BaseUart" + str(self.uart_id))
        self.encoding = encoding
        self.is_open = False
        self.running = False
        self.baud = baud


    def open(self):
        self.is_open = True


    def close(self):
        self.is_open = False
        
        
    def start(self):
        """
        Opens the uart if it's not already open and begins reading from it.
        Messages will be posted to the pubsub 
        """
        if not self.is_open:
            self.open()
        self.running = True

        pubsub.subscribe(Topics.REMOTE_MESSAGE, self._on_pubsub_message, self.pubsub_origin)
        pubsub.subscribe(Topics.TCP_MESSAGE, self._on_pubsub_message, self.pubsub_origin)
        pubsub.subscribe(Topics.TERMINAL_MESSAGE, self._on_pubsub_message, self.pubsub_origin)


    async def _on_pubsub_message(self, payload: str, topic: str, origin: Origin):
        prefix = self.pubsub_origin.name + ":"
        try:
            if(payload.find(prefix) == 0):
                message = payload[len(prefix):]
                self.write(message)
                print(f"tx: {origin.name}: [{message.strip()}]. rx: {self.pubsub_origin.name}")
        except Exception as e:
            print("Error writing to " + self.pubsub_origin.name + ":", e)


    def write(self, message):
        if(self.is_open):
            self._write_impl(message)


    def _write_impl(self, message):
        pass


    async def stop(self):
        """
        Requests the uart to end and waits until it does. 
        """
        self.running = False
        pubsub.unsubscribe(Topics.REMOTE_MESSAGE, self._on_pubsub_message)
        pubsub.unsubscribe(Topics.TCP_MESSAGE, self._on_pubsub_message)
        pubsub.unsubscribe(Topics.TERMINAL_MESSAGE, self._on_pubsub_message)



class HwUart(BaseUart):

    def __init__(self, uart_id = 1, tx_pin = 21, rx_pin = 20, encoding = 'utf-8', baud = DEFAULT_BAUD):
        super().__init__(uart_id, tx_pin, rx_pin, encoding, baud)
        self.uart = None

        self._rx_buffer = micropython.RingIO(512)
        self._tmp_buf = bytearray(64)  # temp buffer for readinto
        self._line_buffer = bytearray()
        self._flag = asyncio.ThreadSafeFlag()
        self._uart_task = None
        
        self.pubsub_origin = PubSub.create_origin("HwUart" + str(self.uart_id))


    def open(self):
        if self.uart == None:
            self.uart = UART(self.uart_id)

        self.uart.init(self.baud, tx = self.tx_pin, rx = self.rx_pin)
        self.uart.irq(trigger = UART.IRQ_RXIDLE, handler = self._irq_handler)
        super().open()


    def _irq_handler(self, uart):
        micropython.schedule(self._on_uart_data, 0)


    def _on_uart_data(self, _):
        try:
            while True:
                n = self.uart.readinto(self._tmp_buf)
                if n is None or n == 0:
                    break
                self._rx_buffer.write(self._tmp_buf)#[:n])
            self._flag.set()
        except Exception as e:
            print("IRQ error:", e)


    def close(self):
        super().close()
        self.uart.deinit()
        self.uart = None
        
        
    def start(self):
        """
        Opens the uart if it's not already open and begins reading from it.
        Messages will be posted to the pubsub 
        """
        super().start()

        if self._uart_task is None or self._uart_task.done():
            self._uart_task = asyncio.create_task(self._read_uart())


    async def _read_uart(self):
        try:
            while self.running:
                await self._flag.wait()
                while self._rx_buffer.any():
                    bytes = self._rx_buffer.read(1)
                    if bytes:
                        char = bytes[0]
                        self._line_buffer.append(char)
                        if char == 10: # ASCII '\n'
                            try:
                                msg = self._line_buffer.decode(self.encoding).strip() + '\r\n'
                                self._line_buffer = bytearray() # reset buffer
                                print("UART received:", msg)
                                pubsub.publish(Topics.UART_MESSAGE, msg, self.pubsub_origin)
                            except Exception as e:
                                print("Decode error:", e)
                                msg = str(self._line_buffer)
                    else:
                        print("Unexpected empty bytes when rx_buffer.any() returned true")
        except Exception as e:
            print("Error in UART read loop:", e)


    def _write_impl(self, message):
        data = message.encode(self.encoding)
        self.uart.write(data)
        self.uart.flush()


    async def stop(self):
        await super().stop()
        res = await self._uart_task


class RmtUart(BaseUart):

    def __init__(self, uart_id = 0, tx_pin = 21, rx_pin = 20, encoding = 'utf-8', baud = DEFAULT_BAUD):
        super().__init__(uart_id, tx_pin, rx_pin, encoding, baud)
        self._rmt = None
        self.pubsub_origin = PubSub.create_origin("RmtUart" + str(self.uart_id))
        self.num_bits = 8
        self.num_stop = 1
        self.tx_pin.value(1)


    def open(self):
        freq = RMT.source_freq() # RMT has 80 mhz base clock. Apparently this might one day be configurable
        num_bits = self.num_bits + 1 + self.num_stop # plus the start bit plus the stop bits

        # below is some algebraicly optimized math to try to find the best numbers given
        # a user-defined baud rate and number of bits
        divisor = math.ceil((freq * num_bits) / (32768 * self.baud))
        counts_per_bit = int(freq / (divisor * self.baud))
        self._bit_time = counts_per_bit * divisor / freq
        self._effective_baud = freq / (counts_per_bit * divisor)
        self._total_tx_time_ms = self._bit_time * (self.num_bits + 1) * 1000

        assert divisor < 256, "divisor larger than 255. Actual size = " + str(divisor)

        self._duration = counts_per_bit # pulse duration in ns
        if self._rmt == None:
            self._rmt = RMT(self.uart_id, pin = self.tx_pin, clock_div = divisor, idle_level = 1)

        # This was the fix for a particularily nasty "bug"? For some reason on the esp32 c3, the RMT was
        # not initialiing to idle_level until _after_ one transmission. This meant the first byte sequence
        # was never being received. So, I sent a single pulse of the shortes possible time, just to kick 
        # it in the ass.
        self._rmt.write_pulses([1], 0)
        self._rmt.wait_done()
        super().open()


    def close(self):
        super().close()
        self._rmt = None


    def _write_impl(self, message):
        # print("start rmt write impl. Message: " + message + " len: " + str(len(message)))

        data = message.encode(self.encoding)
        
        for byte in data:
            print("byte")
            pulses = [self._duration]  # start bit, low because write_pulses starts low
            state = 0
            # create data bits
            for bit in range(8):
                if (byte & 1) == state:
                    pulses[-1] += self._duration # two bits with same value, increase duration
                    assert pulses[-1] < 32768
                else:
                    pulses.append(self._duration)  # alernating bit, add a new pulse
                    state = byte & 1
                byte >>= 1
            #add the stop bits
            if state == 1:
                pulses[-1] += self._duration * self.num_stop
            else:
                pulses.append(self._duration * self.num_stop)
            self._rmt.write_pulses(pulses, 0) # start low 
            self._rmt.wait_done(timeout = math.ceil(self._total_tx_time_ms) + 1) # 1ms extra since this is just a timout
        print("end rmt write impl")


