# uart_async.py
from machine import Pin, UART
import uasyncio as asyncio

# Configure the TX and RX pins:
# - TX on GPIO21, in open-drain mode
# - RX on GPIO20 (input)

# using internal pullup resistor
# tx_pin = Pin(21, mode=Pin.OPEN_DRAIN, pull=Pin.PULL_UP)

# using external pullup
tx_pin = Pin(21, mode=Pin.OPEN_DRAIN)

rx_pin = Pin(20, mode=Pin.IN)


# Defining paramiters the UART transmission and assigning pins:
# - 9600 baud, 8N1 (bits=8, parity=None, stop=1)

uart = UART(
    1,                  # ID of the UART (varies by board/firmware)
    baudrate=9600,
    bits=8,
    parity=None,
    stop=1,
    tx=tx_pin,
    rx=rx_pin
)

async def uart_task():
# Continuously read data from the UART in a loop,
# and optionally write or process it. Maybe adjust sleep delay.

    while True:
    # Check if any bytes are waiting in the buffer
        if uart.any() > 0:
            data = uart.read()
            if data:
                print("Received from UART:", data)
                # we can parse data or queue it somewhere from here.
                # If you need to respond, you can do:
                # uart.write(b"ACK\r\n")
        # Sleep a bit to yield control, then check again
        await asyncio.sleep_ms(50)

def start_uart_task():
# schedule the UART task
# on the asyncio event loop.
    asyncio.create_task(uart_task())
