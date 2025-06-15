import asyncio
import logging
from typing import Optional, Tuple

_LOGGER = logging.getLogger(__name__)


class UDPClient:
    """Async UDP client for sending and receiving UDP packets."""

    def __init__(self, server_host: str, server_port: int):
        self.server_host = server_host
        self.server_port = server_port

    class SimpleClientProtocol(asyncio.DatagramProtocol):
        """Protocol for sending a message without expecting a response."""
        def __init__(self, message: bytes):
            self.message = message

        def connection_made(self, transport):
            transport.sendto(self.message)
            transport.close()

    class EchoClientProtocol(asyncio.DatagramProtocol):
        """Protocol for sending a message and receiving a response."""
        def __init__(self, message: bytes, future: asyncio.Future):
            self.message = message
            self.future = future
            self.transport = None

        def connection_made(self, transport):
            self.transport = transport
            transport.sendto(self.message)

        def datagram_received(self, data, addr):
            if not self.future.done():
                self.future.set_result(data)
            if self.transport:
                self.transport.close()

        def error_received(self, exc):
            if not self.future.done():
                self.future.set_exception(exc)

        def connection_lost(self, exc):
            if not self.future.done():
                self.future.set_exception(ConnectionError("Connection lost"))

    async def send(self, bytes_to_send: bytes) -> None:
        """Send a UDP packet without expecting a response."""
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: self.SimpleClientProtocol(bytes_to_send),
            remote_addr=(self.server_host, self.server_port)
        )
        transport.close()

    async def send_rcv(self, bytes_to_send: bytes) -> Optional[Tuple[bytes, bytes]]:
        """Send a UDP packet and wait for a response."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        transport, _ = await loop.create_datagram_endpoint(
            lambda: self.EchoClientProtocol(bytes_to_send, future),
            remote_addr=(self.server_host, self.server_port)
        )

        try:
            data = await asyncio.wait_for(future, timeout=5.0)
            return data, b'0'  # success marker
        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout: No response from server in 5 seconds.")
            return None
        except Exception as exc:
            _LOGGER.error(f"UDP error: {exc}")
            return None
        finally:
            transport.close()
