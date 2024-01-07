import hashlib
import logging
import random
import struct
from datetime import datetime, timezone
from enum import Enum
from custom_components.alsavopro.const import MODE_TO_CONFIG, NO_WATER_FLUX, WATER_TEMP_TOO_LOW, MAX_UPDATE_RETRIES, \
     MAX_SET_CONFIG_RETRIES
from .udpclient import UDPClient

_LOGGER = logging.getLogger(__name__)


class AlsavoPro:
    """Alsavo Pro data handler."""

    def __init__(self, name, serial_no, ip_address, port_no, password):
        """Init Alsavo Pro data handler."""
        self._name = name
        self._serial_no = serial_no
        self._ip_address = ip_address
        self._port_no = port_no
        self._password = password
        self._data = QueryResponse(0, 0)
        self._session = AlsavoSocketCom()
        self._set_retries = 0
        self._update_retries = 0
        self._online = False

    async def update(self):
        _LOGGER.debug(f"update")
        try:
            await self._session.connect(self._ip_address, int(self._port_no), int(self._serial_no), self._password)
            data = await self._session.query_all()
            if data is not None:
                self._data = data
        except Exception as e:
            if self._update_retries < MAX_UPDATE_RETRIES:
                self._update_retries += 1
                await self.update()
                self._online = True
            else:
                self._update_retries = 0
                _LOGGER.error(f"Unable to update: {e}")
                self._online = False

    async def set_config(self, idx: int, value: int):
        _LOGGER.debug(f"set_config({idx}, {value})")
        try:
            await self._session.connect(self._ip_address, int(self._port_no), int(self._serial_no), self._password)
            await self._session.set_config(idx, value)
        except Exception as e:
            if self._set_retries < MAX_SET_CONFIG_RETRIES:
                self._set_retries += 1
                await self.set_config(idx, value)
                self._online = True
            else:
                self._set_retries = 0
                _LOGGER.error(f"Unable to set config: {idx}, {value} Error: {e}")
                self._online = False

    @property
    def is_online(self) -> bool:
        return self._data.parts > 0

    @property
    def unique_id(self):
        return f"{self._name}_{self._serial_no}"

    @property
    def target_temperature(self):
        return self.get_temperature_from_config(MODE_TO_CONFIG.get(self.operating_mode, 0))

    async def set_target_temperature(self, value: float):
        config_key = MODE_TO_CONFIG.get(self.operating_mode)
        if config_key is not None:
            await self.set_config(config_key, int(value * 10))

    def get_status_value(self, idx: int):
        return self._data.get_status_value(idx)

    def get_config_value(self, idx: int):
        return self._data.get_config_value(idx)

    def get_temperature_from_status(self, idx):
        return self._data.get_status_temperature_value(idx)

    def get_temperature_from_config(self, idx):
        return self._data.get_config_temperature_value(idx)

    @property
    def water_in_temperature(self):
        return self.get_temperature_from_status(16)

    @property
    def water_out_temperature(self):
        return self.get_temperature_from_status(17)

    @property
    def ambient_temperature(self):
        return self.get_temperature_from_status(18)

    @property
    def operating_mode(self):
        return self._data.get_config_value(4) & 3

    @property
    def is_timer_on_enabled(self):
        return self._data.get_config_value(4) & 4 == 4

    @property
    def water_pump_running_mode(self):
        return self._data.get_config_value(4) & 8 == 8

    @property
    def electronic_valve_style(self):
        return self._data.get_config_value(4) & 16 == 16

    @property
    def is_power_on(self):
        return self._data.get_config_value(4) & 32 == 32

    @property
    def power_mode(self):
        return self._data.get_config_value(16)

    @property
    def is_debug_mode(self):
        return self._data.get_config_value(4) & 64 == 64

    @property
    def is_timer_off_enabled(self):
        return self._data.get_config_value(4) & 128 == 128

    @property
    def manual_defrost(self):
        return self._data.get_config_value(5) & 1 == 1

    @property
    def errors(self):
        error = ""
        if self.get_status_value(48) & 0x4 == 0x4:
            error += NO_WATER_FLUX
        if self.get_status_value(49) & 0x400 == 0x400:
            error += WATER_TEMP_TOO_LOW
        return error

    async def set_power_off(self):
        await self.set_config(4, self._data.get_config_value(4) & 0xFFDF)

    async def set_cooling_mode(self):
        await self.set_config(4, (self._data.get_config_value(4) & 0xFFDC) + 32)

    async def set_heating_mode(self):
        await self.set_config(4, (self._data.get_config_value(4) & 0xFFDC) + 33)

    async def set_auto_mode(self):
        await self.set_config(4, (self._data.get_config_value(4) & 0xFFDC) + 34)

    async def set_power_mode(self, value: int):
        await self.set_config(16, value)

    @property
    def name(self):
        return self._name


class PacketHeader:
    """ This is the packet header """
    """ It consists of 16 bytes and have the following attributes: """
    """ - hdr - byte - 0x32 = request, 0x30 = response """
    """ - pad - byte - Padding. Always 0 """
    """ - seq - Int16 - Sequence number (monotonically increasing once session has been set up, otherwise 0) """
    """ - csid - Int32 - ??? """
    """ - dsid - Int32 - ??? """
    """ - cmd - Int16 - Command """
    """ - Payload length - Int16 - """

    def __init__(self, hdr, seq, csid, dsid, cmd, payload_length):
        self.hdr = hdr
        self.pad = 0
        self.seq = seq
        self.csid = csid
        self.dsid = dsid
        self.cmd = cmd
        self.payloadLength = payload_length

    @property
    def is_reply(self):
        return (self.hdr & 2) == 0

    def pack(self):
        # Struct format: char, char, uint16, uint32, uint32, uint16, uint16
        return struct.pack('!BBHIIHH', self.hdr, self.pad, self.seq, self.csid, self.dsid, self.cmd, self.payloadLength)

    @staticmethod
    def unpack(data):
        unpacked_data = struct.unpack('!BBHIIHH', data)
        return PacketHeader(unpacked_data[0], unpacked_data[2], unpacked_data[3], unpacked_data[4], unpacked_data[5],
                            unpacked_data[6])


class Timestamp:
    def __init__(self):
        current_time = datetime.now(timezone.utc)
        self.year = current_time.year
        self.month = current_time.month
        self.day = current_time.day
        self.hour = current_time.hour
        self.min = current_time.minute
        self.sec = current_time.second
        self.tz = 2  # Placeholder

    def pack(self):
        # Struct format: uint16, char, char, char, char, char, char
        return struct.pack('!HBBBBBB', self.year, self.month, self.day, self.hour, self.min, self.sec, self.tz)


class AuthIntro:
    def __init__(self, client_token, serial_inv):
        self.hdr = PacketHeader(0x32, 0, 0, 0, 0xf2, 0x28)
        self.act1, self.act2, self.act3, self.act4 = 1, 1, 2, 0
        self.clientToken = client_token
        self.pumpSerial = serial_inv
        self._uuid = [0x97e8ced0, 0xf83640bc, 0xb4dd57e3, 0x22adc3a0]
        self.timestamp = Timestamp()

    def pack(self):
        packed_hdr = self.hdr.pack()
        packed_uuid = struct.pack('!IIII', *self._uuid)
        packed_data = struct.pack('!BBBBIQ', self.act1, self.act2, self.act3, self.act4, self.clientToken,
                                  self.pumpSerial) + packed_uuid + self.timestamp.pack()
        return packed_hdr + packed_data


class AuthChallenge:
    def __init__(self, hdr, act1, act2, act3, act4, server_token):
        self.hdr = hdr
        self.act1 = act1
        self.act2 = act2
        self.act3 = act3
        self.act4 = act4
        self.serverToken = server_token

    @staticmethod
    def unpack(data):
        # 16 first bytes are header
        packet_hdr = PacketHeader.unpack(data[0:16])

        # Define the format string for unpacking
        format_string = '!BBBBI'  # Adjust to match your structure

        # Unpack the serialized data
        unpacked_data = struct.unpack(format_string, data[16:24])

        # Create a new instance of the class and initialize its attributes
        obj = AuthChallenge(packet_hdr, unpacked_data[0], unpacked_data[1], unpacked_data[2], unpacked_data[3],
                            unpacked_data[4])

        return obj

    @property
    def is_authorized(self):
        return self.act1 == 3 and self.act2 == 0 and self.act3 == 0 and self.act4 == 0


class AuthResponse:
    def __init__(self, csid, dsid, resp):
        # Header fields
        self.hdr = PacketHeader(0x32, 0, csid, dsid, 0xf2, 0x1c)
        self.act1, self.act2, self.act3, self.act4 = 4, 0, 0, 3
        self.timestamp = Timestamp()

        # Response field (as a bytes object)
        self.response = bytes(resp)

    def pack(self):
        packed_data = struct.pack('!BBBB', self.act1, self.act2, self.act3, self.act4)
        return self.hdr.pack() + packed_data + self.response + self.timestamp.pack()


class Payload:
    """ Config, Status or device info-payload packet """
    """ Is part of the QueryResponse packet """
    def __init__(self, data_type, sub_type, size, start_idx, indices):
        self.type = data_type
        self.subType = sub_type
        self.size = size
        self.startIdx = start_idx
        self.indices = indices
        self.data = []

    def get_value(self, idx):
        if idx - self.startIdx < 0 or idx - self.startIdx > self.data.__len__():
            return 0
        return self.data[idx - self.startIdx]

    @staticmethod
    def unpack(data):
        unpacked_data = struct.unpack('!IHHHH', data[0:12])
        obj = Payload(unpacked_data[0], unpacked_data[1], unpacked_data[2], unpacked_data[3], unpacked_data[4])
        if obj.subType == 1 or obj.subType == 2:
            obj.data = struct.unpack('>' + 'H' * (obj.size // 2), data[12:12 + obj.size])
        else:
            obj.startIdx = 0
            obj.indices = 0
            obj.data = struct.unpack('>' + 'H' * (obj.size // 2), data[8:8 + obj.size])
        return obj


class QueryResponse:
    """ Query response containing data payload from heatpump. """
    """ Contains both status and config. """

    def __init__(self, action, parts):
        self.action = action
        self.parts = parts
        self.__payloads = []
        self.__status = None
        self.__config = None
        self.__deviceInfo = None

    def get_status_value(self, idx: int):
        if self.__status is None:
            return 0
        else:
            return self.__status.get_value(idx)

    def get_config_value(self, idx: int):
        if self.__config is None:
            return 0
        else:
            return self.__config.get_value(idx)

    def get_signed_status_value(self, idx: int):
        unsigned_int = self.get_status_value(idx)
        if unsigned_int > 32767:
            return unsigned_int - 65536
        else:
            return unsigned_int

    def get_signed_config_value(self, idx: int):
        unsigned_int = self.get_config_value(idx)
        if unsigned_int > 32767:
            return unsigned_int - 65536
        else:
            return unsigned_int

    def get_status_temperature_value(self, idx: int):
        return self.get_signed_status_value(idx) / 10

    def get_config_temperature_value(self, idx: int):
        return self.get_signed_config_value(idx) / 10

    @staticmethod
    def unpack(data):
        unpacked_data = struct.unpack('!BBH', data[0:4])
        obj = QueryResponse(unpacked_data[0], unpacked_data[1])
        idx = 4

        while idx < data.__len__():
            payload = Payload.unpack(data[idx:])
            if payload.subType == 1:
                obj.__status = payload
            elif payload.subType == 2:
                obj.__config = payload
            if payload.subType == 3:
                obj.__deviceInfo = payload
            obj.__payloads.append(payload)
            idx += payload.size + 8

        return obj


def md5_hash(text):
    """ Simple hashing of password """
    md5 = hashlib.md5()
    md5.update(text.encode())
    return md5.digest()


class ConnectionStatus(Enum):
    Disconnected = 0
    Connected = 1


class AlsavoSocketCom:
    """ Socket communication handler for the Alsavo Pro integration """
    """ Everything is pull-based. """

    def __init__(self):
        self.serverToken = None
        self.DSIS = None
        self.CSID = None
        self.password = None
        self.serialQ = None
        self.clientToken = None
        self.lstConfigReqTime = None
        self.client = None

    async def send_and_receive(self, bytes_to_send):
        _LOGGER.debug(f"send_and_receive())")
        response = await self.client.send_rcv(bytes_to_send)
        _LOGGER.debug(f"Received response")
        return response

    async def send(self, bytes_to_send):
        _LOGGER.debug(f"send())")
        await self.client.send(bytes_to_send)

    async def get_auth_challenge(self):
        auth_intro = AuthIntro(self.clientToken, self.serialQ)
        response = await self.send_and_receive(bytes(auth_intro.pack()))
        return AuthChallenge.unpack(response[0])

    async def send_auth_response(self, ctx):
        resp = AuthResponse(self.CSID, self.DSIS, ctx.digest())
        return await self.send_and_receive(resp.pack())

    async def send_and_rcv_packet(self, payload: bytes, cmd=0xf4):
        _LOGGER.debug(f"send_and_rcv_packet(payload, {cmd})")
        if self.CSID is not None and self.DSIS is not None:
            return await self.send_and_receive(
                PacketHeader(0x32, 0, self.CSID, self.DSIS, cmd, payload.__len__()).pack() + payload
            )
        return None

    async def send_packet(self, payload: bytes, cmd=0xf4):
        _LOGGER.debug(f"send_packet(payload, {cmd})")
        if self.CSID is not None and self.DSIS is not None:
            await self.send(PacketHeader(0x32, 0, self.CSID, self.DSIS, cmd, payload.__len__()).pack() + payload)

    async def query_all(self):
        """ Query all information from the heat pump """
        _LOGGER.debug("socket.query_all")
        resp = await self.send_and_rcv_packet(b'\x08\x01\x00\x00\x00\x02\x00\x2e\xff\xff\x00\x00')
        self.lstConfigReqTime = datetime.now()
        if resp is None:
            raise Exception("query_all: no response")
        return QueryResponse.unpack(resp[0][16:])

    async def set_config(self, idx: int, value: int):
        """ Set configuration values on the heat pump """
        _LOGGER.debug(f"socket.set_config({idx}, {value})")
        idx_h = ((idx >> 8) & 0xff).to_bytes(1, 'big')
        idx_l = (idx & 0xff).to_bytes(1, 'big')
        val_h = ((value >> 8) & 0xff).to_bytes(1, 'big')
        val_l = (value & 0xff).to_bytes(1, 'big')
        await self.send_packet(b'\x09\x01\x00\x00\x00\x02\x00\x2e\x00\x02\x00\x04' + idx_h + idx_l + val_h + val_l)

    async def connect(self, server_ip, server_port, serial, password):
        _LOGGER.debug("Connecting to Alsavo Pro")

        self.clientToken = random.randint(0, 65535)
        self.serialQ = serial
        self.password = password
        self.client = UDPClient(server_ip, server_port)

        _LOGGER.debug("Asking for auth challenge")
        auth_challenge = await self.get_auth_challenge()

        if not auth_challenge.is_authorized:
            raise ConnectionError("Invalid auth challenge packet (pump offline?), disconnecting")

        self.CSID = auth_challenge.hdr.csid
        self.DSIS = auth_challenge.hdr.dsid
        self.serverToken = auth_challenge.serverToken

        _LOGGER.debug(f"Received handshake, CSID={hex(self.CSID)}, DSID={hex(self.DSIS)}, "
                      f"server token {hex(self.serverToken)}")

        ctx = hashlib.md5()
        ctx.update(self.clientToken.to_bytes(4, "big"))
        ctx.update(self.serverToken.to_bytes(4, "big"))
        ctx.update(md5_hash(self.password))

        response = await self.send_auth_response(ctx)

        if response is None or response[0].__len__() == 0:
            raise ConnectionError("Server not responding to auth response, disconnecting.")

        act = int.from_bytes(response[0][16:20], byteorder='little')
        if act != 0x00000005:
            raise ConnectionError("Server returned error in auth, disconnecting")

        _LOGGER.debug("Connected.")
