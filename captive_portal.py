import socket
import uasyncio as asyncio
import network

# Default AP IP
SERVER_IP = '10.0.0.1'

class DNSQuery:
    def __init__(self, data):
        self.data = data
        self.domain = ''
        ini = 12
        lon = data[ini]
        while lon != 0:
            self.domain += data[ini+1:ini+lon+1].decode('utf-8') + '.'
            ini += lon + 1
            lon = data[ini]
        print("DNSQuery domain:", self.domain)

    def response(self, ip):
        packet = self.data[:2] + b'\x81\x80'
        packet += self.data[4:6] + self.data[4:6] + b'\x00\x00\x00\x00'
        packet += self.data[12:]
        packet += b'\xC0\x0C'
        packet += b'\x00\x01\x00\x01\x00\x00\x00\x3C\x00\x04'
        packet += bytes(map(int, ip.split('.')))
        return packet

async def run_dns_server():
    """Start the DNS server to intercept and redirect all queries."""
    udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udps.setblocking(False)
    udps.bind(('0.0.0.0', 53))
    while True:
        try:
            data, addr = udps.recvfrom(4096)
        except OSError:
            await asyncio.sleep_ms(50)
            continue
        print("Incoming DNS request...")
        dns_query = DNSQuery(data)
        # If the domain is 'tinklink.local.', check the STA interface:
        if dns_query.domain.lower() == "tinklink.local.":
            sta = network.WLAN(network.STA_IF)
            if sta.isconnected():
                ip = sta.ifconfig()[0]
                print("Redirecting tinklink.local to STA IP:", ip)
            else:
                ip = SERVER_IP
        else:
            ip = SERVER_IP
        udps.sendto(dns_query.response(ip), addr)
        print("Replying:", dns_query.domain, "->", ip)
    udps.close()

def start_dns_server_task():
    """Convenience function to start the DNS server task."""
    asyncio.create_task(run_dns_server())
