import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

class UDPClientProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.queue = asyncio.Queue()
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        _LOGGER.debug(f"Received UDP packet from {addr}: {data.hex()}")
        self.queue.put_nowait((data, addr))

    def error_received(self, exc):
        _LOGGER.warning(f"UDP error received: {exc}")

    def connection_lost(self, exc):
        _LOGGER.info("UDP connection closed")

class UDPClient:
    def __init__(self, host, port, loop=None):
        self.host = host
        self.port = port
        self.loop = loop or asyncio.get_event_loop()
        self.transport = None
        self.protocol = None

    async def connect(self):
        _LOGGER.debug(f"Connecting UDP to {self.host}:{self.port}")
        transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: UDPClientProtocol(),
            remote_addr=(self.host, self.port)
        )
        self.transport = transport
        self.protocol = protocol

    def sendto(self, data: bytes):
        if self.transport is None:
            raise RuntimeError("UDP transport is not connected.")
        _LOGGER.debug(f"Sending UDP data: {data.hex()}")
        self.transport.sendto(data)

    async def send_rcv(self, data: bytes, timeout=3.0):
        if self.transport is None:
            await self.connect()

        self.sendto(data)
        try:
            response, _ = await asyncio.wait_for(self.protocol.queue.get(), timeout)
            _LOGGER.debug(f"Received response: {response.hex()}")
            return [response]  # ✅ Return a list of bytes to match the caller's expectations
        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout waiting for UDP response")
            return None  # ✅ Return None on timeout instead of an int
