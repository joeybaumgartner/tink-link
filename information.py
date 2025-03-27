import network
import uasyncio as asyncio

# We store the scanned networks here for the control panel.
_scanned_networks = []

async def get_wifi_info():
    """
    Return a dict of relevant WiFi info:
      - 'ssid': The AP SSID
      - 'ip': The AP IP
      - 'sta_connected': Bool
      - 'sta_ssid': Current STA SSID if connected
      - 'sta_ip': STA IP if connected
      - 'available_networks': A list of SSIDs from the last scan
    """
    info_dict = {}

    # AP info if you want to fill
    # (In your code, you might fill from actual AP object or store in global state.)
    info_dict['ssid'] = "TinkLink-Hotspot"
    info_dict['ip'] = "10.0.0.1"

    # STA info
    sta = network.WLAN(network.STA_IF)
    info_dict['sta_connected'] = sta.isconnected()
    if sta.isconnected():
        info_dict['sta_ssid'] = sta.config('essid')
        info_dict['sta_ip'] = sta.ifconfig()[0]
    else:
        info_dict['sta_ssid'] = None
        info_dict['sta_ip'] = "0.0.0.0"

    # Insert the last scanned networks
    # (If _scanned_networks is empty, the Control Panel won't show anything yet.)
    info_dict['available_networks'] = _scanned_networks

    return info_dict

async def do_wifi_scan():
    """
    Perform an actual WiFi scan on STA interface.
    Return a list of SSIDs (strings).
    """
    print("[DEBUG] do_wifi_scan() called, scanning WiFi networks...")

    sta = network.WLAN(network.STA_IF)
    was_active = sta.active()

    if not was_active:
        print("[DEBUG] STA was inactive, activating for scan.")
        sta.active(True)

    results = sta.scan()  # list of tuples: (ssid, bssid, channel, RSSI, authmode, hidden)

    found_ssids = []
    for r in results:
        ssid_bytes = r[0]
        ssid_str = ssid_bytes.decode('utf-8')
        if ssid_str not in found_ssids:
            found_ssids.append(ssid_str)

    if not was_active:
        print("[DEBUG] Deactivating STA after scan.")
        sta.active(False)

    print("[DEBUG] do_wifi_scan() found:", found_ssids)
    return found_ssids

def update_scanned_networks(ssids):
    """
    Update the global scanned networks so that get_wifi_info() can return them.
    """
    global _scanned_networks
    _scanned_networks = ssids
    print("[DEBUG] update_scanned_networks() - now storing:", _scanned_networks)
