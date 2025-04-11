import os
import network
import time
import uasyncio as asyncio
import captive_portal
import web_server
import uart_async
import tcp_async
import telnet_async
import hotspot_control
import information 
from extron_sw_vga import ExtronSwVga
from extron_mav_crosspoint import ExtronMavCp
import json
from retrotink import Retrotink


# AP configuration constants
SERVER_SSID = 'TinkLink-Hotspot'
SERVER_IP = '10.0.0.1'
SERVER_SUBNET = '255.255.255.0'
CONFIG_FILE = "config.json"
SAVED_CONNECTION_FILE = "saved_connection.txt"


def wifi_start_access_point(ip = SERVER_IP, subnet = SERVER_SUBNET, ssid = SERVER_SSID):
    wifi = network.WLAN(network.AP_IF)
    wifi.ifconfig((ip, subnet, ip, ip))
    wifi.active(True)
    wifi.config(essid=ssid, authmode=network.AUTH_OPEN)
    print('AP Network config:', wifi.ifconfig())


def clear_sta_settings():
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        sta.disconnect()
    sta.active(False)
    print("STA settings cleared.")


def connect_saved_network():
    """Reads saved_connection.txt and attempts to connect to that network."""
    try:
        with open(SAVED_CONNECTION_FILE, "r") as f:
            data = f.read()
        lines = data.splitlines()

        if len(lines) >= 2:
            saved_ssid = lines[0]
            saved_password = lines[1]
            print("Attempting to connect to saved network:", saved_ssid)

            sta = network.WLAN(network.STA_IF)
            sta.active(True)  # Must activate before calling config()
            sta.config(dhcp_hostname="tinklink")
            sta.connect(saved_ssid, saved_password)

            timeout = 10
            while timeout > 0 and not sta.isconnected():
                time.sleep(0.5)
                timeout -= 0.5

            if sta.isconnected():
                print("Connected to saved network:", saved_ssid)
                print("STA IP:", sta.ifconfig()[0])
                print("Hostname set to tinklink.local")
            else:
                print("Failed to connect to saved network:", saved_ssid)
        else:
            print("Saved connection file incomplete, clearing STA settings.")
            clear_sta_settings()

    except OSError:
        print("No saved connection found, clearing STA settings.")
        clear_sta_settings()


def get_telnet_config(filename: str) -> dict:
    try:
        with open(filename) as f:
            config = json.load(f)
            return config
    except OSError:
        print("No telnet server setup, continuing...")
        return None
    

def get_config(filename: str = CONFIG_FILE) -> dict:
    try:
        with open(filename) as f:
            config = json.load(f)
            return config
    except OSError:
        print("No config found")
        return None


async def main():
    config = get_config()

    

    # Wifi hotspot

    # -----------------------
    # Below needs to be moved to config.json
    # -----------------------

    hotspot_enabled = config.get("hotspot", {}).get("enabled", True)
    wifi_start_access_point()
    # Allow time for the AP to initialize
    # should move this into an asyncio task so the rest of the app can launch
    time.sleep(1)  
    hotspot_mode = config.get("hotspot", {}).get("mode", hotspot_control.HotspotModes.ALWAYS_ON)
    mode = hotspot_control.get_hotspot_mode()
    print("Hotspot mode at boot:", mode)
    if mode == hotspot_control.HotspotModes.TIMEOUT:
        hotspot_control.start_countdown()
    captive_portal_enabled = config.get("hotspot", {}).get("captivePortalEnabled", True)
    captive_portal.start_dns_server_task()

    # Wifi client/station
    
    # -----------------------
    # Below needs to be moved to config.json
    # -----------------------

    connect_saved_network()

    # Tink Support

    tink_conf = config.get("tink", {})
    tink = Retrotink.create_from_config(tink_conf)
    tink.start()

    # Switcher Support

    switcher_confs = config.get("switchers", {})
    switchers = []
    for switcher_conf in switcher_confs:
        if not switcher_conf.get("enabled", False):
            continue
        switcher = None
        type = switcher_conf.get("type", None)
        if type == "ExtronSwVga":
            try:
                print("Creating ExtronSwVga switcher")    
                switcher = ExtronSwVga.create_from_config(switcher_conf)
                await switcher.start()
            except Exception as e:
                print("Error creating ExtronSwVga switcher: ", e)    
            switchers.append(switcher)
        elif type == "ExtronMavCp":
            try:
                print("Creating ExtronMavCp switcher")    
                switcher = ExtronMavCp.create_from_config(switcher_conf)
                await switcher.start()
            except Exception as e:
                print("Error creating ExtronMavCp switcher: ", e)
            switchers.append(switcher)
            
    # Start servers/tasks

    web_server.start_web_server() # includes remote and terminal websockets

    tcpConfig = config.get("tcpServer", {})
    if tcpConfig.get("enabled", False):
        tcp_async.start_serial_over_tcp_server(port = tcpConfig.get("port", 8023))

    print("Servers running. AP:", SERVER_SSID)
    while True:
        await asyncio.sleep(3600)

asyncio.run(main())
