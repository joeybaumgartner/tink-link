from microdot import Microdot, Response, send_file #Microdot handles web service
from microdot.websocket import with_websocket #websocket Microdot extension
import uasyncio as asyncio #allows aynchronous task handling
import uart_async #async uart tx and rx and machine pin config
import hotspot_control
import information
import network
import os

app = Microdot()

def load_status_template():
    """Load the status response template."""
    try:
        with open("status_response.html", "r") as f:
            return f.read()
    except OSError:
        return None

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

# WebSocket endpoint with added debug prints for remote commands
@app.route('/ws')
@with_websocket
async def ws_endpoint(request, ws):
    print("WebSocket connection established")
    uart_async.chat_clients_websocket.add(ws)

    try:
        while True:
            msg = await ws.receive()
            if msg is None:
                print("WebSocket connection closed by client")
                break

            if msg == "pwr":
                # For power commands, send two messages:
                command1 = "pwr on\r\n"
                command2 = "remote pwr on\r\n"
                await uart_async.broadcast_message(command1, source='websocket')
                await uart_async.broadcast_message(command2, source='websocket')
                print("Broadcasted special power commands:", command1, command2)
            else:
                # For other commands, add the remote prefix and CR/LF
                full_command = "remote " + msg + "\r\n"
                await uart_async.broadcast_message(full_command, source='websocket')
                print("Broadcasted command:", full_command)
    finally:
        uart_async.chat_clients_websocket.discard(ws)
        print("WebSocket client removed")

@app.get('/remote-page')
async def remote_page(request):
    return send_file('static/html/remote.html')

@app.get('/terminal')
async def terminal_page(request):
    return send_file('static/html/terminal.html')

# Terminal WebSocket endpoint for serial commands (no "remote" prefix)
@app.route('/ws_terminal')
@with_websocket
async def ws_terminal(request, ws):
    print("Terminal WebSocket connection established")
    uart_async.chat_clients_websocket.add(ws)
    try:
        while True:
            msg = await ws.receive()
            print("Terminal WebSocket received:", msg)
            if msg is None:
                print("Terminal WebSocket connection closed by client")
                break
            # Send command with CR+LF without the "remote" prefix
            full_command = msg + "\r\n"
            await uart_async.broadcast_message(full_command, source='terminal')
            print("Broadcasted terminal command:", full_command)
    finally:
        uart_async.chat_clients_websocket.discard(ws)
        print("Terminal WebSocket client removed")

# Control panel page with dynamic content
@app.get('/control-panel')
async def control_panel(request):
    try:
        with open('/control_panel.html', 'r') as f:
            html = f.read()
        wifi_info = await information.get_wifi_info()
        available = wifi_info.get('available_networks', [])
        options_list = [f'<option value="{ssid}">{ssid}</option>' for ssid in available]
        if not options_list:
            options_list = ['<option value="">Please press "Scan For Networks" to populate this list.</option>']
        options = "\n".join(options_list)
        hotspot_mode_value = hotspot_control.get_hotspot_mode()
        html = html.replace('{{NETWORK_OPTIONS}}', options)
        html = html.replace('{{SSID}}', wifi_info.get('ssid', 'Unknown'))
        html = html.replace('{{DOMAIN}}', 'tinklink.local')
        html = html.replace('{{IP}}', wifi_info.get('ip', '0.0.0.0'))
        html = html.replace('{{HOTSPOT_MODE}}', hotspot_mode_value)
        sta_connected = wifi_info.get('sta_connected', False)
        sta_status = "Connected" if sta_connected else "Not Connected"
        sta_ssid = wifi_info.get('sta_ssid', 'N/A') or "N/A"
        sta_ip = wifi_info.get('sta_ip', '0.0.0.0')
        html = html.replace('{{STA_STATUS}}', sta_status)
        html = html.replace('{{STA_SSID}}', sta_ssid)
        html = html.replace('{{STA_IP}}', sta_ip)
        try:
            os.stat("saved_connection.txt")
            saved_connection_exists = True
            with open("saved_connection.txt", "r") as f:
                lines = f.read().splitlines()
            saved_ssid = lines[0] if len(lines) >= 2 else None
        except OSError:
            saved_connection_exists = False
            saved_ssid = None
        saved_connection_display = f"Saved Connection: {saved_ssid}" if saved_connection_exists and saved_ssid else "Saved Connection: None"
        html = html.replace('{{SAVED_CONNECTION}}', saved_connection_display)
        connected_buttons = ""
        if sta_connected:
            connected_buttons = (
                '<form id="disconnect-form" method="POST" action="/disconnect">'
                '<button type="submit">Disconnect</button>'
                '</form>'
            )
        html = html.replace('{{DISCONNECT_BUTTON}}', connected_buttons)
        saved_buttons = ""
        if sta_connected:
            if saved_connection_exists and saved_ssid:
                if sta_ssid == saved_ssid:
                    saved_buttons = (
                        '<form id="delete-connection-form" method="POST" action="/delete_connection">'
                        '<button type="submit">Delete Saved Connection</button>'
                        '</form>'
                    )
                else:
                    saved_buttons = (
                        '<form id="overwrite-connection-form" method="POST" action="/save_connection">'
                        f'<input type="hidden" name="network" value="{sta_ssid}">'
                        '<input type="hidden" name="password" value="">'
                        '<button type="submit">Overwrite Saved Connection</button>'
                        '</form>'
                    )
                    saved_buttons += (
                        '<form id="delete-connection-form" method="POST" action="/delete_connection">'
                        '<button type="submit">Delete Saved Connection</button>'
                        '</form>'
                    )
            else:
                global last_valid_password
                password_field = f'<input type="hidden" name="password" value="{last_valid_password if last_valid_password else ""}">'
                saved_buttons = (
                    '<form id="save-connection-form" method="POST" action="/save_connection">'
                    f'<input type="hidden" name="network" value="{sta_ssid}">'
                    + password_field +
                    '<button type="submit">Save Connection</button>'
                    '</form>'
                )
                saved_buttons += '<br><i>Connect to network and click Save Connection to connect on boot.</i>'
        else:
            if saved_connection_exists:
                saved_buttons += (
                    '<form id="delete-connection-form" method="POST" action="/delete_connection">'
                    '<button type="submit">Delete Saved Connection</button>'
                    '</form>'
                )
            saved_buttons += '<br><i>Connect to network and click Save Connection to connect on boot.</i>'
        html = html.replace('{{SAVED_CONNECTION_BUTTON}}', saved_buttons)
        return Response(html, headers={
            'Content-Type': 'text/html',
            'Cache-Control': 'no-cache, no-store, must-revalidate'
        })
    except OSError:
        return Response("control_panel.html not found", status_code=404)

# Endpoint to scan WiFi networks
@app.post('/scan_networks')
async def scan_networks(request):
    print("[DEBUG] /scan_networks called. Scanning WiFi networks...")
    template = load_status_template()
    if template is None:
        return Response("Template not found", status_code=500)
    scanning_message = "Scanning WiFi Connections. Please Wait..."
    html = template.replace("{{MESSAGE}}", scanning_message)
    found_ssids = await information.do_wifi_scan()
    information.update_scanned_networks(found_ssids)
    return Response(html, headers={'Content-Type': 'text/html'})

# Set hotspot mode status response
@app.post('/set_hotspot_mode')
async def set_hotspot_mode(request):
    mode = request.form.get('mode')
    if mode not in ["5-minute_time_out", "always_on"]:
        return Response("Invalid mode", status_code=400)
    display_mode = "5-Minute Time-Out" if mode == "5-minute_time_out" else "Always On"
    try:
        with open("hotspot_mode.txt", "w") as f:
            f.write(display_mode)
    except Exception as e:
        return Response("Failed to set hotspot mode: " + str(e), status_code=500)
    if display_mode == "5-Minute Time-Out":
        hotspot_control.start_countdown()
    else:
        hotspot_control.cancel_countdown()
    template = load_status_template()
    if template is None:
        return Response("Template not found", status_code=500)
    html = template.replace("{{MESSAGE}}", "Hotspot Mode Set To " + display_mode)
    return Response(html, headers={'Content-Type': 'text/html'})

# Connect to a network
@app.post('/connect')
async def connect_home_network(request):
    global last_valid_password
    ssid = request.form.get('network')
    password = request.form.get('password')
    if not ssid or not password:
        template = load_status_template()
        if template is None:
            return Response("Template not found", status_code=500)
        html = template.replace("{{MESSAGE}}", "You must select a valid SSID and enter a password to continue.")
        return Response(html, headers={'Content-Type': 'text/html'})
    
    sta = network.WLAN(network.STA_IF)
    # Activate interface first, then set the hostname.
    sta.active(True)
    sta.config(dhcp_hostname="tinklink")
    
    if sta.isconnected():
        sta.disconnect()
        await asyncio.sleep(1)
    
    try:
        sta.connect(ssid, password)
    except Exception as e:
        return Response(f"Error during connect: {e}", status_code=500)
    
    timeout = 10
    while timeout > 0 and not sta.isconnected():
        await asyncio.sleep(1)
        timeout -= 1
    
    template = load_status_template()
    if template is None:
        return Response("Template not found", status_code=500)
    
    if sta.isconnected():
        last_valid_password = password
        message = "Connected"
    else:
        # Attempt to fall back to the previously saved connection if available
        try:
            with open("saved_connection.txt", "r") as f:
                lines = f.read().splitlines()
            if len(lines) >= 2:
                saved_ssid = lines[0]
                saved_password = lines[1]
            else:
                saved_ssid = None
                saved_password = None
        except OSError:
            saved_ssid = None
            saved_password = None
        
        if saved_ssid and saved_ssid == ssid:
            print("Attempting fallback connection using saved credentials.")
            sta.disconnect()
            await asyncio.sleep(1)
            sta.connect(saved_ssid, saved_password)
            fallback_timeout = 10
            while fallback_timeout > 0 and not sta.isconnected():
                await asyncio.sleep(1)
                fallback_timeout -= 1
            if sta.isconnected():
                last_valid_password = saved_password
                message = "Connected using saved credentials"
            else:
                message = "WiFi Connection Failed (Check Password)"
                sta.disconnect()
                await asyncio.sleep(1)
                sta.active(False)
                await asyncio.sleep(1)
                sta.active(True)
                sta.config(dhcp_hostname="tinklink")
        else:
            message = "WiFi Connection Failed (Check Password)"
            sta.disconnect()
            await asyncio.sleep(1)
            sta.active(False)
            await asyncio.sleep(1)
            sta.active(True)
            sta.config(dhcp_hostname="tinklink")
    
    html = template.replace("{{MESSAGE}}", message)
    return Response(html, headers={'Content-Type': 'text/html'})

# Disconnect from a network
@app.post('/disconnect')
async def disconnect_home_network(request):
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        sta.disconnect()
        await asyncio.sleep(1)
    timeout = 5
    while timeout > 0 and sta.isconnected():
        await asyncio.sleep(1)
        timeout -= 1
    message = "Disconnected" if not sta.isconnected() else "Disconnect failed. Please try again."
    template = load_status_template()
    if template is None:
        return Response("Template not found", status_code=500)
    html = template.replace("{{MESSAGE}}", message)
    return Response(html, headers={'Content-Type': 'text/html'})

# Save connection details
@app.post('/save_connection')
async def save_connection(request):
    network_name = request.form.get('network')
    password = request.form.get('password')
    if not network_name or not password:
        return Response("Missing network or password", status_code=400)
    try:
        with open("saved_connection.txt", "w") as f:
            f.write(f"{network_name}\n{password}")
    except OSError as e:
        return Response(f"Failed to save connection (OS error): {e}", status_code=500)
    except Exception as e:
        return Response(f"Failed to save connection: {e}", status_code=500)
    template = load_status_template()
    if template is None:
        return Response("Template not found", status_code=500)
    html = template.replace("{{MESSAGE}}", "Connection Saved")
    return Response(html, headers={'Content-Type': 'text/html'})

# Delete saved connection details
@app.post('/delete_connection')
async def delete_connection(request):
    try:
        os.remove("saved_connection.txt")
    except OSError as e:
        return Response("Error deleting saved connection: " + str(e), status_code=500)
    template = load_status_template()
    if template is None:
        return Response("Template not found", status_code=500)
    html = template.replace("{{MESSAGE}}", "Connection Deleted")
    return Response(html, headers={'Content-Type': 'text/html'})

@app.errorhandler(404)
def not_found(request):
    return Response(status_code=302, headers={'Location': '/remote-page'})
    
def start_web_server():
    # Start both the web server and the UART loopback reader concurrently.
    server_task = asyncio.create_task(app.start_server(host='0.0.0.0', port=80))
    return server_task
