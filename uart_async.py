from machine import Pin, UART
import uasyncio as asyncio

# Global sets for shared chat room clients
chat_clients_serial_over_tcp = set()      # serial_over_tcp client writer objects
chat_clients_websocket = set()              # WebSocket objects

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
    rx=rx_pin
)

async def broadcast_message(message, source=None):
    """
    Broadcast the raw message to all connected endpoints and log a single summary line.
    The message is sent to:
      - serial_over_tcp (raw TCP) clients
      - WebSocket clients
      - UART (if source isn't 'uart', to avoid echo)
    The log summarizes which endpoints received the message.
    """
    recipients = []
    
    # Send to serial_over_tcp clients:
    for writer in list(chat_clients_serial_over_tcp):
        try:
            writer.write(message.encode('utf-8'))
            await writer.drain()
            recipients.append("raw_tcp")
        except Exception as e:
            print("Error broadcasting to raw_tcp client:", e)
    
    # Send to WebSocket clients:
    for ws in list(chat_clients_websocket):
        try:
            await ws.send(message)
            recipients.append("WebSocket")
        except Exception as e:
            print("Error broadcasting to WebSocket client:", e)
    
    # Write to UART if the message did not originate from UART (avoid echo)
    if source != 'uart':
        try:
            uart.write(message.encode('utf-8'))
            recipients.append("UART")
        except Exception as e:
            print("Error writing to UART:", e)
    
    # Log a single summary line
    clean_message = message.strip()
    print(f"tx: {source}: [{clean_message}]. rx: {', '.join(recipients)}")

async def uart_task():
    """
    Continuously read data from the UART.
    When data is received, decode and broadcast it without modification.
    (No "remote " helper is added for UART data.)
    """
    while True:
        if uart.any() > 0:
            data = uart.read()
            if data:
                try:
                    msg = data.decode('utf-8').strip()
                except Exception:
                    msg = str(data)
                print("UART received:", msg)
                # Broadcast the raw UART message with a CR/LF appended
                await broadcast_message(msg + "\r\n", source='uart')
        await asyncio.sleep_ms(50)

def start_uart_task():
    """
    Schedule the UART reading task.
    """
    asyncio.create_task(uart_task())

async def handle_serial_over_tcp(reader, writer):
    """
    Handle a serial_over_tcp connection.
    Read lines from the client and broadcast them unchanged.
    (No "remote " prefix is added for serial_over_tcp messages.)
    """
    addr = writer.get_extra_info('peername')
    print("serial_over_tcp client connected:", addr)
    chat_clients_serial_over_tcp.add(writer)
    try:
        writer.write(b"Connected to TinkLink Serial Over TCP Terminal\r\n")
        await writer.drain()
        while True:
            line = await reader.readline()
            if not line:
                break
            # Process the incoming message without adding any prefix
            msg = line.decode('utf-8').strip().replace('\t', '')
            print("serial_over_tcp received:", msg)
            # Broadcast the message as received with CR/LF
            await broadcast_message(msg + "\r\n", source='serial_over_tcp')
        print("serial_over_tcp client finished sending data:", addr)
    except Exception as e:
        print("serial_over_tcp error:", e)
    finally:
        chat_clients_serial_over_tcp.discard(writer)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        print("serial_over_tcp client disconnected:", addr)

def start_serial_over_tcp_server(port=8023):
    """
    Start the serial_over_tcp server on the given port.
    """
    print("Starting serial_over_tcp server on port", port)
    return asyncio.create_task(asyncio.start_server(handle_serial_over_tcp, '0.0.0.0', port))

# Usage:
# In your main application code, call:
#   start_uart_task()
#   start_serial_over_tcp_server(port=8023)
#
# For the WebSocket (remote) endpoint, in your web server module, import:
#   chat_clients_websocket and broadcast_message from this module.
# In that WebSocket endpoint, if you want to add the "remote " helper, do it there before calling broadcast_message,
# for example:
#    await broadcast_message("remote " + msg + "\r\n", source='web')
#
# This way, UART and serial_over_tcp messages are transmitted unmodified,
# while the remote (web) channel can include the helper prefix as desired.
