import asyncio
import logging

_LOGGER = logging.getLogger(__name__)


class UDPClient:
    """Async UDP client with retry and broadcast support."""

    def __init__(self, server_host, server_port, use_broadcast=False):
        self.server_host = server_host
        self.server_port = server_port
        self.use_broadcast = use_broadcast
        self.loop = asyncio.get_event_loop()

    class SimpleClientProtocol(asyncio.DatagramProtocol):
        def __init__(self, message):
            self.message = message
            self.transport = None

        def connection_made(self, transport):
            self.transport = transport
            self.transport.sendto(self.message)
            self.transport.close()

    class EchoClientProtocol(asyncio.DatagramProtocol):
        def __init__(self, message, future):
            self.message = message
            self.future = future
            self.transport = None

        def connection_made(self, transport):
            self.transport = transport
            self.transport.sendto(self.message)

        def datagram_received(self, data, addr):
            if not self.future.done():
                self.future.set_result(data)
            self.transport.close()

        def error_received(self, exc):
            if not self.future.done():
                self.future.set_exception(exc)

        def connection_lost(self, exc):
            if not self.future.done():
                self.future.set_exception(ConnectionError("Connection lost"))

    async def send_rcv(self, bytes_to_send, retries=3):
        """Send data and wait for response, with retries."""
        for attempt in range(1, retries + 1):
            future = self.loop.create_future()

            try:
                transport, protocol = await self.loop.create_datagram_endpoint(
                    lambda: self.EchoClientProtocol(bytes_to_send, future),
                    remote_addr=(self.server_host, self.server_port),
                    allow_broadcast=self.use_broadcast,
                )

                _LOGGER.debug("UDP send attempt %d to %s:%d", attempt, self.server_host, self.server_port)
                data = await asyncio.wait_for(future, timeout=5.0)

                _LOGGER.debug("UDP received response (attempt %d): %s", attempt, data.hex())
                return data, b'0'

            except asyncio.TimeoutError:
                _LOGGER.warning("UDP timeout on attempt %d: no response", attempt)
            except Exception as e:
                _LOGGER.error("UDP error on attempt %d: %s", attempt, str(e))
            finally:
                if 'transport' in locals():
                    transport.close()

        _LOGGER.error("All %d UDP attempts failed", retries)
        return None

    async def send(self, bytes_to_send):
        """Send UDP message without waiting for a response."""
        try:
            transport, protocol = await self.loop.create_datagram_endpoint(
                lambda: self.SimpleClientProtocol(bytes_to_send),
                remote_addr=(self.server_host, self.server_port),
                allow_broadcast=self.use_broadcast,
            )
            _LOGGER.debug("UDP fire-and-forget sent to %s:%d", self.server_host, self.server_port)
        except Exception as e:
            _LOGGER.error("UDP send error: %s", str(e))
        else:
            transport.close()
