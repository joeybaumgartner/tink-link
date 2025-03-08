TinkLink is an open source project to add Wi-Fi remote control capability to the RetroTINK-4K. Utilizing an ESP32-C3 and a custom HD-15 PCB designed by Jeff Chen, the TinkLink connects to the Tink4K's HD-15 input and allows users to send serial UART commands from virtually any device with WIFI and a web browser to simulate the Tink4K's remote control functions. A passthrough female VGA port allows video signals to connect to the Tink4K alongside the TinkLink's Serial UART commands.

TinkLink is coded in MicroPython and relies on the Microdot web server library, as well as some DNS handling code heavily borrowed from Mycropython-Captiveportal (https://github.com/metachris/micropython-captiveportal).

Software Components Description:
- "captive_portal.py": This handles DNS requests and is part of creating the captive portal feature.
- "web_server.py" Serves HTML pages and files while also handling WebSocket data transmission.
- "uart_async.py" Sets up and sends UART data down the ESP32-C3's GPIO pins.
- "remote.html" The main remote web page, and home to the "small-remote.png" image map and UART short name commands (pwr, prof3, etc) that web_server + uart_async use to send commands to the Tink4K.
- "remote.js": Handles WebSocket configuration for "remote.html", as well as the logic for long-press repeating command function (set to 1 second hold, 50ms repeating).
- "main.py": Configures WIFI configuration and starts the access point, along with the main asyncio task loop.
- "small-remote.png": A compressed PNG of the RetroTINK-4K's remote to tap on in "remote.html".

Configuring ESP32-C3 Software
TinkLink requires MicroPython to be installed on your ESP32-C3. A good tutorial for this process using the Thonnny IDE can be found here: https://bhave.sh/micropython-install-esp32/

TinkLink requires Microdot.
Your ESP32-C3 file system root should have a "microdot" folder containing:
- helpers.py
- microdot.py
- websocket.py
- __init.py

Your root file system will also need to contain the files outlined in the "Software Components" section, hosted at this repository.

Hardware
TinkLink PCB Required Components: 
- Female VGA (HD-15) Ports x2: Digikey (expensive) K61X-E15S-NJ-VESA or AliExpress Alternative (cheap) https://www.aliexpress.us/item/2255800410490932.html
- 10k Ohm 0603 Surface mount resistor (for pullup on TX).
- ESP32-C3 MCU: The TinkLink PCB is physically compatible with he Seeed Studio Xiao ESP32-C3, or a generic AliExpress "TENSTARROBOT C3 Super Mini" board.

TinkLink UART Notes
UART TX: The TinkLink sends messages over a TTL-Level, 3.3v open drain configuration output, to the RetroTINK-4K sing standard 9600 baud, "8N1" serial communication.
UART RX: While wired to receive data back from the Tink4K, it is currently an unused feature.

Standard PCB Configuration
- On front face of PCB, solder 10k Ohm pullup resistor on "Pullup TX" pads When using external pullup resistor, ensure that internal pullup resistor is disabled in "uart_async.py".
- On font face of PCB, apply 3.3v pullup voltage by bridging TX triangle pad to center.
- On back face of PCB, solder bridge both triangle pads to center pads to use Xiao ESP32-C3, or solder unlabeled pads to center pads for C3 Super Mini configuration.
- Align Xiao or C3 Super Mini MCU to top right pins on front face of PCB. Attach MCU to PCB by soldering 5v, Ground, 3.3v, TX and RX pins. Note that The Super Mini MCU will have TX and RX on the bottom left of the PCB, while the Xiao MCU will have TX and RX on opposing left and right bottom corners.

Connecting to the RetroTINK-4K:
Use a VGA cable to connect the TX side of the board's HD-15 port to the RetroTink-4K's HD-15 input. Apply power to the MCU using a standard 5v power supply and USB-C cable. Passthrough VGA video and serial communication devices will plug into the TinkLink PCB's RX HD-15 jack. From your WIFI enabled device, connect to "TinkLink-HotSpot" and a captive portal page should launch. If no page launches, open your browser and navigate to "tinklink.local". You should see the RetroTINK remote in your browser.







