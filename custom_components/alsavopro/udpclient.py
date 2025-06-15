import asyncio
import logging
from typing import Optional, Tuple

_LOGGER = logging.getLogger(__name__)


class UDPClient:
    """Async UDP client for sending and receiving UDP packets with retry logic."""

    def __init__(self, server_host: str, server_port: int):
        self.server_host = server_host
        self.server_port = server_port

    class SimpleClientProtocol(asyncio.DatagramProtocol):
        def __init__(self, message: bytes):
            self.message = message

        def connection_made(self, transport):
            transport.sendto(self.message)
            transport.close()

    class EchoClientProtocol(asyncio.DatagramProtocol):
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

    async def send(self, bytes_to_send: bytes, retries: int = 3, retry_delay: float = 1.0) -> bool:
        """Send a UDP packet with retries."""
        for attempt in range(retries):
            try:
                loop = asyncio.get_running_loop()
                transport, _ = await loop.create_datagram_endpoint(
                    lambda: self.SimpleClientProtocol(bytes_to_send),
                    remote_addr=(self.server_host, self.server_port)
                )
                transport.close()
                return True
            except Exception as e:
                _LOGGER.warning(f"UDP send attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(retry_delay)
        _LOGGER.error("All UDP send attempts failed.")
        return False

    async def send_rcv(
        self, bytes_to_send: bytes, retries: int = 3, retry_delay: float = 1.0
    ) -> Optional[Tuple[bytes, bytes]]:
        """Send a UDP packet and wait for a response, with retries."""
        for attempt in range(retries):
            try:
                loop = asyncio.get_running_loop()
                future = loop.create_future()
                transport, _ = await loop.create_datagram_endpoint(
                    lambda: self.EchoClientProtocol(bytes_to_send, future),
                    remote_addr=(self.server_host, self.server_port)
                )
                try:
                    data = await asyncio.wait_for(future, timeout=5.0)
                    return data, b'0'
                finally:
                    transport.close()
            except (asyncio.TimeoutError, ConnectionError) as e:
                _LOGGER.warning(f"Attempt {attempt + 1} failed with timeout or connection error: {e}")
            except Exception as e:
                _LOGGER.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                break  # Don't retry on unknown errors
            await asyncio.sleep(retry_delay)
        _LOGGER.error("All UDP send/receive attempts failed.")
        return None
