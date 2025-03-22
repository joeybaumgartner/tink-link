from microdot import Microdot, Response, send_file #Microdot handles web service
from microdot.websocket import with_websocket #websocket Microdot extension
import uasyncio as asyncio #allows aynchronous task handling
import uart_async #async uart tx and rx and machine pin config

app = Microdot()

@app.get('/')
async def index(request):
    return Response(status_code=302, headers={'Location': '/remote-page'})

# Handler for all static content (CSS, JS, HTML, images, etc.)
@app.route('/static/<path:path>')
async def static(request, path):
    if '..' in path:
        # directory traversal is not allowed
        return 'Not found', 404
    return send_file('static/' + path, max_age=1)

@app.route('/generate_204')
async def generate_204(request):
    return Response('', status_code=302, headers={'Location': 'http://10.0.0.1/'})

@app.route('/ncsi.txt')
async def ncsi_txt(request):
    return Response('No Connectivity', headers={'Content-Type': 'text/plain'})

@app.route('/hotspot-detect.html')
async def hotspot_detect(request):
    return Response('', status_code=302, headers={'Location': 'http://10.0.0.1/'})

@app.route('/library/test/success.html')
async def apple_success(request):
    return Response('', status_code=302, headers={'Location': 'http://10.0.0.1/'})

@app.route('/ws')
@with_websocket
async def ws_endpoint(request, ws):
    print("WebSocket connection established")
    while True:
        msg = await ws.receive()
        if msg is None:
            break

        # Special handler for the "pwr" command, two for the price of one message
        if msg == "pwr":
            wake_pwr = msg + " on\n"
            data = wake_pwr.encode('utf-8')
            written = uart_async.uart.write(data)
            print("UART TX:", repr(wake_pwr))
        
        # Always send the general command regardless of the message
        full_command = "remote " + msg + "\n"
        data = full_command.encode('utf-8')
        written = uart_async.uart.write(data)
        if written == len(data):
            print("UART TX:", repr(full_command))
        else:
            print("UART send error:", repr(full_command),
                  "bytes written:", written, "expected:", len(data))

@app.get('/remote-page')
async def remote_page(request):
    return send_file('static/html/remote.html')

@app.errorhandler(404)
def not_found(request):
    return Response(status_code=302, headers={'Location': '/remote-page'})
    
def start_web_server():
    # Start both the web server and the UART loopback reader concurrently.
    server_task = asyncio.create_task(app.start_server(host='0.0.0.0', port=80))
    return server_task
