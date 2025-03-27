import uasyncio as asyncio
import network

# Global variable to store the countdown task.
hotspot_countdown_task = None

def get_hotspot_mode():
    """
    Retrieve and validate the hotspot mode from file.

    Allowed display values are "Always On" and "5-Minute Time-Out".
    If the file doesn't exist or contains an invalid value,
    it will be created/reset to "Always On".
    """
    allowed_modes = ["Always On", "5-Minute Time-Out"]
    try:
        with open("hotspot_mode.txt", "r") as f:
            mode = f.read().strip()
        if mode not in allowed_modes:
            mode = "Always On"
            print("Invalid HotSpot mode detected. Reverting to Always On.")
            with open("hotspot_mode.txt", "w") as f:
                f.write(mode)
    except OSError:
        mode = "Always On"
        with open("hotspot_mode.txt", "w") as f:
            f.write(mode)
        print("No HotSpot File detected. Setting to Always On.")
    return mode

async def _hotspot_countdown():
    # Wait 5 minutes (300 seconds) from the moment the countdown starts.
    await asyncio.sleep(300)
    if get_hotspot_mode() == "5-Minute Time-Out":
        ap = network.WLAN(network.AP_IF)
        if ap.active():
            ap.active(False)
            print("Hotspot disabled after 5-minute countdown.")

def start_countdown():
    """Cancel any existing countdown and start a new one."""
    global hotspot_countdown_task
    if hotspot_countdown_task is not None:
        hotspot_countdown_task.cancel()
    hotspot_countdown_task = asyncio.create_task(_hotspot_countdown())
    print("Countdown started.")

def cancel_countdown():
    """Cancel the countdown task if running."""
    global hotspot_countdown_task
    if hotspot_countdown_task is not None:
        hotspot_countdown_task.cancel()
        hotspot_countdown_task = None
        print("Countdown cancelled.")
