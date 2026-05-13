import asyncio
import logging

_LOGGER = logging.getLogger(__name__)


class UDPClient:
    """Async UDP client that reuses one socket for the full session."""

    def __init__(self, server_host, server_port):
        self.server_host = server_host
        self.server_port = server_port
        self._transport = None
        self._protocol = None

    class _Protocol(asyncio.DatagramProtocol):
        def __init__(self):
            self._pending: asyncio.Future | None = None

        def datagram_received(self, data, addr):
            if self._pending is not None and not self._pending.done():
                self._pending.set_result(data)

        def error_received(self, exc):
            if self._pending is not None and not self._pending.done():
                self._pending.set_exception(exc)

        def connection_lost(self, exc):
            if self._pending is not None and not self._pending.done():
                self._pending.set_exception(ConnectionError("Connection lost"))

    async def open(self):
        """Open the UDP socket (call once per session)."""
        loop = asyncio.get_running_loop()
        self._protocol = self._Protocol()
        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: self._protocol,
            remote_addr=(self.server_host, self.server_port),
        )

    def close(self):
        """Close the UDP socket."""
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    async def send_rcv(self, bytes_to_send):
        """Send bytes and wait for a response on the same socket."""
        loop = asyncio.get_running_loop()
        self._protocol._pending = loop.create_future()
        self._transport.sendto(bytes_to_send)
        try:
            data = await asyncio.wait_for(self._protocol._pending, timeout=10.0)
            return data, b'0'
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout: No response from server in 10 seconds.")
            return None

    async def send(self, bytes_to_send):
        """Send bytes without waiting for a response."""
        self._transport.sendto(bytes_to_send)
