# main.py
import network
import time
import uasyncio as asyncio
import captive_portal
import web_server
import uart_async

# AP configuration
SERVER_SSID = 'TinkLink-Hotspot'
SERVER_IP = '10.0.0.1'
SERVER_SUBNET = '255.255.255.0'

def wifi_start_access_point():
    wifi = network.WLAN(network.AP_IF)
    wifi.active(True)
    wifi.ifconfig((SERVER_IP, SERVER_SUBNET, SERVER_IP, SERVER_IP))
    wifi.config(essid=SERVER_SSID, authmode=network.AUTH_OPEN)
    print('AP Network config:', wifi.ifconfig())

async def main():
    # Initialize the WiFi Access Point
    wifi_start_access_point()
    time.sleep(1)  # Allow time for the AP to initialize

    # Start the captive portal DNS server as a background task
    captive_portal.start_dns_server_task()

    # Start the Microdot web server
    web_server.start_web_server()
    # start UART server
    uart_async.start_uart_task()

    print("Servers running. AP:", SERVER_SSID)
    while True:
        await asyncio.sleep(3600)

# Run the main event loop
asyncio.run(main())
