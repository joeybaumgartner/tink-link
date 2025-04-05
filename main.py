import os
import network
import time
from extron_mav_crosspoint import ExtronMavCrosspoint
import uasyncio as asyncio
import captive_portal
import web_server
import uart_async
import tcp_async
import telnet_async
import hotspot_control
import information 
from extron_sw_vga import ExtronSwVga
import json

# AP configuration constants
SERVER_SSID = 'TinkLink-Hotspot'
SERVER_IP = '10.0.0.1'
SERVER_SUBNET = '255.255.255.0'

SAVED_CONNECTION_FILE = "saved_connection.txt"

def wifi_start_access_point():
    wifi = network.WLAN(network.AP_IF)
    wifi.ifconfig((SERVER_IP, SERVER_SUBNET, SERVER_IP, SERVER_IP))
    wifi.active(True)
    wifi.config(essid=SERVER_SSID, authmode=network.AUTH_OPEN)
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

def connect_to_telnet(filename: str) -> dict:
    try:
        with open(filename) as f:
            config = json.load(f)
            return config
    except OSError:
        print("No telnet server setup, continuing...")
        return None

async def main():
    wifi_start_access_point()
    time.sleep(1)  # Allow time for the AP to initialize

    # Check hotspot mode and start countdown if needed.
    mode = hotspot_control.get_hotspot_mode()
    print("Hotspot mode at boot:", mode)
    if mode == hotspot_control.HotspotModes.TIMEOUT:
        hotspot_control.start_countdown()

    # Attempt to connect to any saved network
    connect_saved_network()

    # Start servers/tasks
    captive_portal.start_dns_server_task()
    web_server.start_web_server()
    uart = uart_async.Hw_Uart(0)
    uart.start()
    extron = ExtronSwVga(uart)
    extron.subscribe()

    config = connect_to_telnet("telnet_config.json")

    if config:
        telnet = telnet_async.TelnetConnection(config["hostname"], config["port"], config["username"], config["password"], config["init_string"])
        telnet.start()

        extroncp = ExtronMavCrosspoint(telnet)
        extroncp.subscribe()

    tcp_async.start_serial_over_tcp_server(port=8023)

    print("Servers running. AP:", SERVER_SSID)
    while True:
        await asyncio.sleep(3600)

asyncio.run(main())
