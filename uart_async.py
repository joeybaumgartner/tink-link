from machine import Pin, UART
import uasyncio as asyncio
from pubsub import pubsub, PubSub, Topics, Origin


pubsub_uart_origin = PubSub.create_origin("uart")

# Configure UART TX and RX pins
tx_pin = Pin(21, mode=Pin.OPEN_DRAIN)
rx_pin = Pin(20, mode=Pin.IN)

# Initialize UART with 9600 baud, 8N1
uart = UART(
    1,
    baudrate=9600,
    bits=8,
    parity=None,
    stop=1,
    tx=tx_pin,
    rx=rx_pin,
    timeout=100
)

async def on_message(payload: str, topic: str, origin: Origin):
    # Write to UART if the message did not originate from UART (avoid echo)
    # Pubsub already guarantees not to deliver messages to same origin so no check needed
    try:
        uart.write(payload.encode('utf-8'))
    except Exception as e:
        print("Error writing to UART:", e)
    clean_message = payload.strip()
    print(f"tx: {origin.name}: [{clean_message}]. rx: {pubsub_uart_origin.name}")

pubsub.subscribe(Topics.WS_MESSAGE, on_message, pubsub_uart_origin)
pubsub.subscribe(Topics.TCP_MESSAGE, on_message, pubsub_uart_origin)
pubsub.subscribe(Topics.TERMINAL_MESSAGE, on_message, pubsub_uart_origin)


async def uart_task():
    """
    Continuously read data from the UART.
    When data is received, decode and broadcast it without modification.
    (No "remote " helper is added for UART data.)
    """
    while True:
        if uart.any() > 0:
            data = uart.readline()
            if data:
                try:
                    msg = data.decode('utf-8').strip()
                    # Strip removes the trailing CR/LF, add it back
                    msg = msg + "\r\n"
                except Exception:
                    msg = str(data)
                print("UART received:", msg)
                pubsub.publish(Topics.UART_MESSAGE, msg, pubsub_uart_origin)
                
        await asyncio.sleep_ms(50)

def start_uart_task():
    """
    Schedule the UART reading task.
    """
    asyncio.create_task(uart_task())


# Usage:
# In your main application code, call:
#   start_uart_task()
#
# For the remote endpoint import:
#   from pubsub import pubsub, PubSub, Topics, Origin
# In that endpoint, if you want to add the "remote " helper, do it there before calling broadcast_message,
# for example:
#    pubsub.publish("/ws/message", "remote " + msg + "\r\n", "websocket")
#
# Check the doc comments on pubsub for more information on how to use
#
# This way, UART and serial_over_tcp messages are transmitted unmodified,
# while the remote (web) channel can include the helper prefix as desired.
