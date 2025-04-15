import json
from microdot import Microdot, Response, send_file #Microdot handles web service
from microdot.websocket import with_websocket #websocket Microdot extension
import uasyncio as asyncio #allows aynchronous task handling
import hotspot_control
import information
import network
import os
from pubsub import getPubSub, PubSub, Topics, Origin
from utils import  Utils, CONFIG_FILE

app = Microdot()
temp_buf = bytearray(1024)
utils = Utils()

@app.get('/')
async def index(request):
    return Response(status_code=302, headers={'Location': '/remote-page'})

# Handler for all static content (CSS, JS, HTML, images, etc.)
# Images are handled in 1K chunks
@app.route('/static/<path:path>')
async def static(request, path):
    
    if '..' in path:
        # directory traversal is not allowed
        return 'Not found', 404
    if(path == "images"):
        try:
            def file_iterator():
                with open(path, 'rb') as f:
                    while True:
                        count = f.readinto(temp_buf)
                        if count == 0:
                            break
                        yield temp_buf[0: count]

            return Response(file_iterator(), headers={'Content-Type': 'image/png'})
        except OSError:
            return Response(f"{path} not found", status_code=404)
    else:
        return send_file('static/' + path, max_age=1)

@app.route('/generate_204')
async def generate_204(request):
    return Response('', status_code=302, headers={'Location': 'http://10.0.0.1/'})

@app.route('/ncsi.txt')
async def ncsi_txt(request):
    return Response('No Connectivity', headers={'Content-Type': 'text/plain'})

@app.route('/hotspot-detect.html')
async def hotspot_detect(request):
    return Response("<html><body>Redirecting</body></html>", status_code=302, headers={'Location': '/control-panel'})

@app.route('/library/test/success.html')
async def apple_success(request):
    return Response('', status_code=302, headers={'Location': 'http://10.0.0.1/'})

# WebSocket endpoint with added debug prints for remote commands

pubsub_remote_origin = None
remote_websockets = None
async def _on_message_remote(payload: str, topic: str, origin: Origin):
    # Send to WebSocket clients:
    global remote_websockets
    for ws in remote_websockets:
        message = origin.name + ":" + payload
        try:
            await ws.send(message)
            print(f"tx: {origin.name}: [{message.strip()}]. rx: {pubsub_remote_origin.name}")
        except Exception as e:
            print("Error broadcasting to remote client:", e)

@app.route('/ws')
@with_websocket
async def ws_endpoint(request, ws):
    print("WebSocket connection established")
    global remote_websockets
    remote_websockets.add(ws)

    try:
        while True:
            msg = await ws.receive()
            if msg is None:
                print("WebSocket connection closed by client")
                break
            elif msg == "pwr":
                full_command = "pwr on\r\n"
            else:
                full_command = "remote " + msg + "\r\n"

            getPubSub().publish(Topics.REMOTE_MESSAGE, full_command, pubsub_remote_origin)
    finally:
        remote_websockets.remove(ws)
        print("WebSocket client removed")

@app.get('/remote-page')
async def remote_page(request):
    return send_file('/static/html/remote.html')

@app.get('/terminal')
async def terminal_page(request):
    return send_file('/static/html/terminal.html')

# Terminal WebSocket endpoint for serial commands (no "remote" prefix)

pubsub_terminal_origin = None
terminal_websockets = None

async def _on_message_terminal(payload: any, topic: str, origin: Origin):
    # Send to WebSocket clients:
    global terminal_websockets
    for ws in terminal_websockets:
        message = f"[{origin.name}] {topic} > {str(payload)}"
        try:
            await ws.send(message)
            print(f"tx: {origin.name}: [{message.strip()}]. rx: {pubsub_terminal_origin.name}")
        except Exception as e:
            print("Error broadcasting to terminal client:", e)


@app.route('/ws_terminal')
@with_websocket
async def ws_terminal(request, ws):
    print("Terminal WebSocket connection established")
    global terminal_websockets
    terminal_websockets.add(ws)
    try:
        while True:
            msg = await ws.receive()
            print("Terminal WebSocket received:", msg)
            if msg is None:
                print("Terminal WebSocket connection closed by client")
                break
            # Terminal javascript code appends "\r\n" to the message, so no need to add it here
            print("Broadcasting terminal command:", msg)
            getPubSub().publish(Topics.TERMINAL_MESSAGE, msg, pubsub_terminal_origin)
            
    finally:
        terminal_websockets.remove(ws)
        print("Terminal WebSocket client removed")

@app.route('/control-panel-data')
async def control_panel_data(request):
    wifi_info = await information.get_wifi_info()
    hotspot_mode_value = hotspot_control.get_hotspot_mode()

    try:
        data = utils.get_config()
        saved_connection_exists = True
        saved_ssid = data["wirelessClient"]["ssid"]
    except KeyError:
        saved_connection_exists = False
        saved_ssid = None

    ssid_info = { 
        "hotspot_ssid": wifi_info.get('ssid', 'unknown'),
        "domain": "tinklink.local",
        "ip": wifi_info.get('ip', '0.0.0.0'),
        "hotspot_mode": hotspot_mode_value,
        "saved_ssid": saved_ssid if saved_connection_exists and saved_ssid else "None"
    }
    
    connected = wifi_info.get('sta_connected', False)
    sta = {
         "sta_status": "Connected" if connected else "Not Connected",
         "sta_ssid": wifi_info.get('sta_ssid', 'N/A') or "N/A",
         "sta_ip": wifi_info.get('sta_ip', '0.0.0.0')
    }
    
    control_panel_data = {
        "connected": connected,
        "ssid_info": ssid_info, 
        "sta": sta, 
        "saved_connection_exists": saved_connection_exists
    }

    return json.dumps(control_panel_data), 200, { "Content-Type": "application/json"}

# Control panel page with dynamic content
@app.route('/control-panel')
async def control_panel(request):
    try:
        with open('/static/html/control_panel.html', 'r') as f:
            html = f.read()
        wifi_info = await information.get_wifi_info()
        #available = wifi_info.get('available_networks', [])
        #options_list = [f'<option value="{ssid}">{ssid}</option>' for ssid in available]
        #if not options_list:
        #    options_list = ['<option value="">Please press "Scan For Networks" to populate this list.</option>']
        #options = "\n".join(options_list)
        hotspot_mode_value = hotspot_control.get_hotspot_mode()
        #html = html.replace('{{NETWORK_OPTIONS}}', options)
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

@app.get('/get-config')
async def get_json_config(request):
    return utils.get_config()

@app.post('/save-config')
async def save_config(request):

    data = utils.get_config()
    payload = request.json
    print(payload)
    try:
        key = payload["formName"]
        data[key] = payload[key]

        utils.write_config(data)
    except Exception as e:
        print(f"Could not update configuration: {e}")
        return { 'Error': f'Could not update configuration {e}' }

    return { 'ok': 'Configuration Saved' }

@app.get('/scan_networks')
async def get_networks(request):
    found_ssids = await information.do_wifi_scan()
    information.update_scanned_networks(found_ssids)
    return json.dumps(found_ssids), 200, {'Content-Type': 'application/json' }

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
    print("Attempting to connect")
    global last_valid_password
    print(f"json is {request.json}")
    ssid = request.json['wirelessClient']['ssid']
    password = request.json['wirelessClient']['password']

    if not ssid or not password:
        return { "error": "You must select a valid SSID and enter a password to continue." }, 500
    
    sta = network.WLAN(network.STA_IF)
    # Activate interface first, then set the hostname.
    sta.active(True)
    sta.config(dhcp_hostname="tinklink")
    
    if sta.isconnected():
        sta.disconnect()
        await asyncio.sleep(1)
    
    try:
        print("trying to connect")
        sta.connect(ssid, password)
    except Exception as e:
        return { "error": f"Error during connect: {e}" }, 500
    
    timeout = 10
    while timeout > 0 and not sta.isconnected():
        await asyncio.sleep(1)
        timeout -= 1
    
    if sta.isconnected():
        last_valid_password = password
        message = "Connected"

        # Attempt to save the connection on first connect attempt
        try:
            data = utils.get_config()
            data["wirelessClient"] = request.json["wirelessClient"]
            utils.write_config(data)
            return { "ok": "Connection saved." }
        except OSError as e:
            print(f"Failed to save connection (OS Error): {e}")
            return { "error": f"Failed to save connection (OS Error): {e}" }, 500
        except Exception as e:
            print(f"Failed to save connection (OS Error): {e}")
            return { "error": f"Failed to save connection: {e}" }, 500
    else:
        # Attempt to fall back to the previously saved connection if available
        try:
            print("Attempt fallback")
            data = utils.get_config()

            saved_ssid = data["wirelessClient"]["ssid"]
            saved_password = data["wirelessClient"]["password"]
            
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

                return { "error": message}, 500
        else:
            message = "WiFi Connection Failed (Check Password)"
            sta.disconnect()
            await asyncio.sleep(1)
            sta.active(False)
            await asyncio.sleep(1)
            sta.active(True)
            sta.config(dhcp_hostname="tinklink")

            return { "error": message}, 500

        return { "ok": message }

# Disconnect from a network
@app.post('/disconnect')
async def disconnect_home_network(request):
    print("calling disconnect")
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        sta.disconnect()
        await asyncio.sleep(1)
    timeout = 5
    while timeout > 0 and sta.isconnected():
        await asyncio.sleep(1)
        timeout -= 1

    message = "Disconnected" if not sta.isconnected() else "Disconnect failed. Please try again."
    return json.dumps({ "ok": message }), 200, {'Content-Type': 'application/json' }

# Save connection details
@app.post('/save_connection')
async def save_connection(request):
    credentials = request.json

    if not credentials["network_name"] or not credentials["password"]:
        # code 400?, should be 500?
        return { "error": "Missing network name or password" }
    try:
        data = utils.get_config()
        data["wirelessClient"] = request.json
        utils.write_config(data)

        return { "ok": "Connection Saved" }
    except OSError as e:
        return { "error": f"Failed to save connection {e}" }, 500
    except Exception as e:
        return { "error": f"Failed to save connection {e}" }, 500

# Delete saved connection details
@app.post('/delete_connection')
async def delete_connection(request):
    try:
        data = utils.get_config()
        data["wirelessClient"] = None
        utils.write_config(data)
        return { "ok": "Saved Connection Deleted" }
    except OSError as e:
        return { "error": f"Error Deleting Saved Connection: str{e}" }, 500

@app.errorhandler(404)
def not_found(request):
    return Response(status_code=302, headers={'Location': '/remote-page'})
    
def start_web_server():
    global pubsub_terminal_origin
    global terminal_websockets
    pubsub_terminal_origin = PubSub.create_origin("terminal")
    terminal_websockets = set()
    
    global pubsub_remote_origin
    global remote_websockets
    pubsub_remote_origin = PubSub.create_origin("remote")
    remote_websockets = set()

    getPubSub().subscribe("/*", _on_message_terminal, pubsub_terminal_origin)

    # Start both the web server and the UART loopback reader concurrently.
    server_task = asyncio.create_task(app.start_server(host='0.0.0.0', port=80))
    return server_task
