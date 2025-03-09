<img src="https://github.com/Patrick-Working/tink-link/blob/tinklink2025/images/tinklinkpcb.png" width="300" align="left"> 
<img src="https://github.com/Patrick-Working/tink-link/blob/tinklink2025/images/PXL_20250309_002008740~2.jpg" width="300"> 

**TinkLink** is an open source project to add Wi-Fi remote control capability to the [RetroTINK-4K](https://www.retrotink.com/product-page/retrotink-4k). Utilizing an ESP32-C3 and a custom PCB designed by [Jeff Chen](https://github.com/jeffqchen), the TinkLink connects to the Tink4K's HD-15 input and allows users to send serial UART commands from virtually any device with WIFI and a web browser to simulate the Tink4K's remote control functions. A passthrough female VGA port allows video signals to connect to the Tink4K alongside the TinkLink's Serial UART commands.

The TinkLink is built to run on the [Seeed Studio's Xiao ESP32-C3](https://www.seeedstudio.com/Seeed-XIAO-ESP32C3-p-5431.html) MCU, as well as [TENSTARROBOT's C3 Super Mini](https://www.aliexpress.us/item/3256807499475367.html).

TinkLink is coded in MicroPython and relies on the [Microdot](https://github.com/miguelgrinberg/microdot) web server library, as well as some DNS handling code heavily borrowed from [Mycropython-Captiveportal](https://github.com/metachris/micropython-captiveportal).

## **Software Components**
- _"captive_portal.py_": This handles DNS requests and is part of creating the captive portal feature.
- _"web_server.py"_: Serves HTML pages and files while also handling WebSocket data transmission.
- _"uart_async.py"_: Sets up and sends UART data down the ESP32-C3's GPIO pins.
- _"remote.html"_: The main remote web page, and home to the "small-remote.png" image map and UART short name commands (pwr, prof3, etc) that web_server + uart_async use to send commands to the Tink4K.
- _"remote.js"_: Handles WebSocket configuration for "remote.html", as well as the logic for long-press repeating command function (set to 1 second hold, 50ms repeating).
- _"main.py"_: Configures WIFI and starts the access point, along with the main asyncio task loop.
- _"small-remote.png"_: A compressed PNG of the RetroTINK-4K's remote to tap on in "remote.html".

### **Configuring ESP32-C3 Software**
TinkLink requires **MicroPython** to be installed on your ESP32-C3. A good tutorial for this process using the Thonny IDE [can be found here]( https://bhave.sh/micropython-install-esp32/).

TinkLink requires [Microdot](https://github.com/miguelgrinberg/microdot). Clone or download the required files and place them on your ESP32-C3.
Your ESP32-C3 file system root should have a _**"microdot"**_ folder containing:
- _"helpers.py"_
- _"microdot.py"_
- _"websocket.py"_
- _"\__init\__.py"_

Your root file system will also need to contain the files outlined in the **"Software Components"** section, hosted at this repository.

## **Hardware**

The TinkLink is built on a PCB designed by Jeff Chen. Gerber files to have a PCB produced are located in this repository in the **"PCB"** folder. 

### **PCB Required Components:**
- Female VGA (HD-15) Ports x2: [Digikey K61X-E15S-NJ-Vtory](https://www.digikey.com/en/products/detail/kycon-inc/K61X-E15S-NJ-VESA/10247235) or a cheaper [AliExpress Alternative](https://www.aliexpress.us/item/2255800410490932.html).
- 10k Ohm 0603 Surface mount resistor (for pullup on TX).
- ESP32-C3 MCU: The TinkLink PCB is physically compatible with the [Xiao ESP32-C3](https://www.seeedstudio.com/Seeed-XIAO-ESP32C3-p-5431.html) MCU, as well as the [TENSTARROBOT's C3 Super Mini](https://www.aliexpress.us/item/3256807499475367.html).

### **TinkLink UART Notes**
- UART TX: The TinkLink sends messages over a TTL-Level, 3.3v open drain configuration output, to the RetroTINK-4K using standard 9600 baud, "8N1" serial communication.
- UART RX: While wired to receive data back from the Tink4K, it is currently an unused feature.

### **Standard PCB Configuration**
<img src="https://github.com/Patrick-Working/tink-link/blob/030408ee8ff43b22a2d360c7d0949b32d40c8e6b/images/standard%20assembly.jpg" width="300"> 

- On front face of PCB, solder 10k Ohm pullup resistor on "Pullup TX" pads When using external pullup resistor, ensure that internal pullup resistor is disabled in _"uart_async.py"_.

- Bridge the two pads directy under the **"Pullup TX"** label to enable the pullup routing circuit.

- On font face of the PCB, apply 3.3v pullup voltage by bridging the **Right 3.3v Pad** to **Center**. (Do not use the the 5V pad option, indicated by the triangle label on the pad).

- On back face of the PCB, solder bridge both triangle pads to center pads to use Xiao ESP32-C3, or solder unlabeled pads to center pads for C3 Super Mini configuration.

- Align Xiao or C3 Super Mini MCU to top right pins on front face of PCB. Attach MCU to PCB by soldering 5v, Ground, 3.3v, TX and RX pins. Note that The Super Mini MCU will have TX and RX on the bottom left of the PCB, while the Xiao MCU will have TX and RX on opposing left and right bottom corners.

## **Connecting to the RetroTINK-4K**
Use a VGA cable to connect the TX side of the board's HD-15 port to the RetroTink-4K's HD-15 input. Apply power to the MCU using a standard 5v power supply and USB-C cable. Passthrough VGA video and serial communication devices will plug into the TinkLink PCB's RX HD-15 jack. From your WIFI enabled device, connect to "TinkLink-HotSpot" and a captive portal page should launch. If no page launches, open your browser and navigate to "tinklink.local". You should see the RetroTINK remote in your browser.
