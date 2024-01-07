import asyncio


class UDPClient:
    """ Async UDP client """
    def __init__(self, server_host, server_port):
        self.server_host = server_host
        self.server_port = server_port
        self.loop = asyncio.get_event_loop()

    class SimpleClientProtocol(asyncio.DatagramProtocol):
        # Sending only
        def __init__(self, message):
            self.message = message
            self.transport = None

        def connection_made(self, transport):
            self.transport = transport
            self.transport.sendto(self.message)
            self.transport.close()

    class EchoClientProtocol(asyncio.DatagramProtocol):
        # Send and receive
        def __init__(self, message, future):
            self.message = message
            self.future = future
            self.transport = None

        def connection_made(self, transport):
            self.transport = transport
            self.transport.sendto(self.message)

        def datagram_received(self, data, addr):
            self.future.set_result(data)
            self.transport.close()

        def error_received(self, exc):
            self.future.set_exception(exc)

        def connection_lost(self, exc):
            if not self.future.done():
                self.future.set_exception(ConnectionError("Connection lost"))

    async def send_rcv(self, bytes_to_send):
        future = self.loop.create_future()
        transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: self.EchoClientProtocol(bytes_to_send, future),
            remote_addr=(self.server_host, self.server_port)
        )

        try:
            data = await asyncio.wait_for(future, timeout=5.0)
            return data, b'0'
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout: No response from server in 5 seconds.")
            return None
        finally:
            transport.close()

    async def send(self, bytes_to_send):
        transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: self.SimpleClientProtocol(bytes_to_send),
            remote_addr=(self.server_host, self.server_port)
        )
        transport.close()
