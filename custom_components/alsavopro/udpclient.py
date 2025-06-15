import asyncio
import logging
import socket

_LOGGER = logging.getLogger(__name__)


class UDPClient:
    """Async UDP client for Alsavo Pro integration."""

    def __init__(self, server_host, server_port, enable_broadcast=False):
        self.server_host = server_host
        self.server_port = server_port
        self.enable_broadcast = enable_broadcast
        self.loop = asyncio.get_event_loop()

    class SimpleClientProtocol(asyncio.DatagramProtocol):
        """UDP protocol for sending only."""
        def __init__(self, message):
            self.message = message
            self.transport = None

        def connection_made(self, transport):
            self.transport = transport
            self.transport.sendto(self.message)
            self.transport.close()

    class EchoClientProtocol(asyncio.DatagramProtocol):
        """UDP protocol for sending and receiving."""
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
        """Send and receive a UDP packet with retry support."""
        for attempt in range(1, retries + 1):
            future = self.loop.create_future()
            try:
                _LOGGER.debug("UDP send_rcv attempt %d to %s:%s", attempt, self.server_host, self.server_port)
                transport, protocol = await self.loop.create_datagram_endpoint(
                    lambda: self.EchoClientProtocol(bytes_to_send, future),
                    remote_addr=(self.server_host, self.server_port),
                    allow_broadcast=self.enable_broadcast
                )

                data = await asyncio.wait_for(future, timeout=5.0)
                _LOGGER.debug("Received UDP response: %s", data.hex())
                return data, b'0'

            except asyncio.TimeoutError:
                _LOGGER.warning("Timeout on attempt %d: No response from %s:%s", attempt, self.server_host, self.server_port)
            except Exception as e:
                _LOGGER.error("Error on attempt %d: %s", attempt, str(e))
            finally:
                if 'transport' in locals():
                    transport.close()

        _LOGGER.error("All %d UDP attempts failed to %s:%s", retries, self.server_host, self.server_port)
        return None

    async def send(self, bytes_to_send):
        """Send a UDP packet without expecting a response."""
        try:
            _LOGGER.debug("Sending UDP packet to %s:%s", self.server_host, self.server_port)
            transport, protocol = await self.loop.create_datagram_endpoint(
                lambda: self.SimpleClientProtocol(bytes_to_send),
                remote_addr=(self.server_host, self.server_port),
                allow_broadcast=self.enable_broadcast
            )
        except Exception as e:
            _LOGGER.error("UDP send failed: %s", str(e))
        else:
            transport.close()
