import asyncio
import logging

_LOGGER = logging.getLogger(__name__)


class UDPClient:
    """Async UDP client with support for retries and optional broadcast."""

    def __init__(self, server_host: str, server_port: int, use_broadcast: bool = False):
        self.server_host = server_host
        self.server_port = server_port
        self.use_broadcast = use_broadcast
        self.loop = asyncio.get_event_loop()

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
            self.transport.sendto(self.message)

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
                self.future.set_exception(exc or ConnectionError("UDP connection lost"))

    async def send_rcv(self, bytes_to_send: bytes, retries: int = 3, timeout: float = 5.0) -> bytes | None:
        """Send data and await response with retry support."""
        for attempt in range(1, retries + 1):
            future = self.loop.create_future()
            transport = None

            try:
                transport, _ = await self.loop.create_datagram_endpoint(
                    lambda: self.EchoClientProtocol(bytes_to_send, future),
                    remote_addr=(self.server_host, self.server_port),
                    allow_broadcast=self.use_broadcast,
                )

                _LOGGER.debug("UDP send attempt %d to %s:%d", attempt, self.server_host, self.server_port)
                data = await asyncio.wait_for(future, timeout=timeout)
                _LOGGER.debug("UDP response received: %s", data.hex())
                return data

            except asyncio.TimeoutError:
                _LOGGER.warning("UDP timeout on attempt %d", attempt)
            except Exception as e:
                _LOGGER.error("UDP error on attempt %d: %s", attempt, str(e))
            finally:
                if transport:
                    transport.close()

        _LOGGER.error("All %d UDP attempts failed", retries)
        return None

    async def send(self, bytes_to_send: bytes):
        """Fire-and-forget send of a UDP message."""
        transport = None
        try:
            transport, _ = await self.loop.create_datagram_endpoint(
                lambda: self.SimpleClientProtocol(bytes_to_send),
                remote_addr=(self.server_host, self.server_port),
                allow_broadcast=self.use_broadcast,
            )
            _LOGGER.debug("UDP message sent to %s:%d", self.server_host, self.server_port)
        except Exception as e:
            _LOGGER.error("UDP send error: %s", str(e))
        finally:
            if transport:
                transport.close()
