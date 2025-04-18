import uasyncio as asyncio
from pubsub import getPubSub, PubSub, Topics, Origin

# Global sets for shared chat room clients
chat_clients_serial_over_tcp = set()      # serial_over_tcp client writer objects

pubsub_tcp_origin = PubSub.create_origin("tcp")

async def on_message(payload: str, topic: str, origin: Origin):
    # Send to serial_over_tcp clients:
    for writer in list(chat_clients_serial_over_tcp):
        try:
            writer.write(payload.encode('utf-8'))
            await writer.drain()
            #recipients.append("raw_tcp")
        except Exception as e:
            print("Error broadcasting to raw_tcp client:", e)
    clean_message = payload.strip()
    print(f"tx: {origin.name}: [{clean_message}]. rx: {pubsub_tcp_origin.name}")

getPubSub().subscribe(Topics.UART_MESSAGE, on_message, pubsub_tcp_origin)
getPubSub().subscribe(Topics.REMOTE_MESSAGE, on_message, pubsub_tcp_origin)
getPubSub().subscribe(Topics.TERMINAL_MESSAGE, on_message, pubsub_tcp_origin)

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
            getPubSub().publish(Topics.TCP_MESSAGE, msg, pubsub_tcp_origin)
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