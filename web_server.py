from microdot import Microdot, Response #Microdot handles web service
from microdot.websocket import with_websocket #websocket Microdot extension
import uasyncio as asyncio #allows aynchronous task handling
import uart_async #async uart tx and rx and machine pin config

app = Microdot()

@app.route('/')
async def index(request):
    return Response(status_code=302, headers={'Location': '/remote-page'})

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

@app.route('/small-remote-image')
async def small_remote_image(request):
    image_path = '/small-remote.png'
    try:
        def file_iterator(): #breaks up large files into chunks to not run out of ram
            with open(image_path, 'rb') as f:
                while True:
                    chunk = f.read(1024)
                    if not chunk:
                        break
                    yield chunk
        return Response(file_iterator(), headers={'Content-Type': 'image/png'})
    except OSError:
        return Response("small-remote.png not found", status_code=404)

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

@app.route('/remote-page')
async def remote_page(request):
    file_path = '/remote.html'
    try:
        with open(file_path, 'r') as f:
            html = f.read()
        return Response(html, headers={'Content-Type': 'text/html'})
    except OSError:
        return Response("remote.html not found", status_code=404)

@app.errorhandler(404)
def not_found(request):
    return Response(status_code=302, headers={'Location': '/remote-page'})

@app.route('/remote.js')
async def remote_js(request):
    file_path = '/remote.js'
    try:
        with open(file_path, 'r') as f:
            js = f.read()
        return Response(js, headers={'Content-Type': 'application/javascript'})
    except OSError:
        return Response("remote.js not found", status_code=404)
    
def start_web_server():
    # Start both the web server and the UART loopback reader concurrently.
    server_task = asyncio.create_task(app.start_server(host='0.0.0.0', port=80))
    return server_task
