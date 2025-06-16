import asyncio
import logging
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

_LOGGER = logging.getLogger(__name__)


class UDPClient:
    """Async UDP client for Home Assistant with retry and broadcast support."""

    def __init__(self, server_host, server_port, use_broadcast=False):
        self.server_host = server_host
        self.server_port = server_port
        self.use_broadcast = use_broadcast

    class SimpleClientProtocol(asyncio.DatagramProtocol):
        def __init__(self, message):
            self.message = message

        def connection_made(self, transport):
            transport.sendto(self.message)
            transport.close()

    class EchoClientProtocol(asyncio.DatagramProtocol):
        def __init__(self, message, future):
            self.message = message
            self.future = future

        def connection_made(self, transport):
            self.transport = transport
            self.transport.sendto(self.message)

        def datagram_received(self, data, addr):
            if not self.future.done():
                self.future.set_result(data)
            self.transport.close()

        def error_received(self, exc):
            if not self.future.done():
                self.future.set_exception(UpdateFailed(f"UDP error received: {exc}"))

        def connection_lost(self, exc):
            if not self.future.done():
                self.future.set_exception(UpdateFailed("UDP connection lost unexpectedly"))

    async def send_rcv(self, bytes_to_send: bytes, retries: int = 3, timeout: float = 5.0) -> bytes:
        """Send data and wait for response. Raise on failure (used with DataUpdateCoordinator)."""
        for attempt in range(1, retries + 1):
            future = asyncio.get_running_loop().create_future()
            transport = None
            try:
                transport, _ = await asyncio.get_running_loop().create_datagram_endpoint(
                    lambda: self.EchoClientProtocol(bytes_to_send, future),
                    remote_addr=(self.server_host, self.server_port),
                    allow_broadcast=self.use_broadcast,
                )

                _LOGGER.debug("UDP send attempt %d to %s:%d", attempt, self.server_host, self.server_port)
                data = await asyncio.wait_for(future, timeout=timeout)

                _LOGGER.debug("UDP received response (attempt %d): %s", attempt, data.hex())
                return data

            except asyncio.TimeoutError:
                _LOGGER.warning("UDP timeout on attempt %d: no response", attempt)
            except Exception as e:
                _LOGGER.error("UDP error on attempt %d: %s", attempt, str(e))
            finally:
                if transport:
                    transport.close()

        raise UpdateFailed(f"All {retries} UDP attempts failed to {self.server_host}:{self.server_port}")

    async def send(self, bytes_to_send: bytes) -> None:
        """Send UDP message without waiting for a response."""
        transport = None
        try:
            transport, _ = await asyncio.get_running_loop().create_datagram_endpoint(
                lambda: self.SimpleClientProtocol(bytes_to_send),
                remote_addr=(self.server_host, self.server_port),
                allow_broadcast=self.use_broadcast,
            )
            _LOGGER.debug("UDP fire-and-forget sent to %s:%d", self.server_host, self.server_port)
        except Exception as e:
            _LOGGER.error("UDP send error (fire-and-forget): %s", str(e))
            raise HomeAssistantError(f"UDP send error: {e}")
        finally:
            if transport:
                transport.close()
