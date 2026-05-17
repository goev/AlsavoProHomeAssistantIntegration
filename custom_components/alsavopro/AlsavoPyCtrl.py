import asyncio
import hashlib
import logging
import secrets
import struct
from datetime import datetime, timezone

from .const import (
    MODE_TO_CONFIG,
    ALARM_REGISTER_48,
    ALARM_REGISTER_49,
    ALARM_REGISTER_50,
    DEV_TYPE_STATUS_IDX,
    DEV_TYPE_FREQALL,
    DEV_TYPE_FREQCH,
)
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
        self._online = False
        # Serialize read-modify-write on config register 4 (mode/power/timer bits).
        self._config4_lock = asyncio.Lock()

    async def _ensure_connected(self):
        """Auth and establish a session if we don't have one. Idempotent."""
        await self._session.connect(
            self._ip_address, int(self._port_no), int(self._serial_no), self._password
        )

    async def _with_session_retry(self, op, *args):
        """
        Run `op(*args)` against the current session. If it fails (likely
        expired session or transient socket error), invalidate the session,
        re-auth once, and retry. Reads (query_all) reuse the session across
        polls; writes (set_config) call disconnect() before invoking this
        helper so they always start from a fresh handshake.
        """
        try:
            await self._ensure_connected()
            return await op(*args)
        except Exception as first_err:
            _LOGGER.debug(
                "Session call failed (%s), re-authing and retrying once", first_err
            )
            self._session.disconnect()
            await asyncio.sleep(2)
            await self._ensure_connected()
            return await op(*args)

    async def update(self):
        _LOGGER.debug("update")
        try:
            data = await self._with_session_retry(self._session.query_all)
        except Exception:
            self._online = False
            raise
        if data is None:
            self._online = False
            raise ConnectionError("Empty response from heat pump")
        self._data = data
        self._online = True

    async def set_config(self, idx: int, value: int):
        _LOGGER.debug("set_config(%s, %s)", idx, value)
        # The pump only commits config writes when made on a freshly
        # authenticated session: reusing a CSID/DSID from a prior poll gets
        # an ACK back but no state change. Force a fresh handshake before
        # every write to match the behaviour of the official Android app.
        self._session.disconnect()
        try:
            await self._with_session_retry(self._session.set_config, idx, value)
            self._online = True
        except Exception:
            self._online = False
            raise
        # The pump also invalidates the session immediately after a write —
        # the next query on the same CSID/DSID returns a truncated packet
        # that fails parsing. Drop the session now so the follow-up read
        # does a fast fresh handshake instead of paying the failure-retry
        # penalty (~2 s sleep + re-auth).
        self._session.disconnect()

    @property
    def is_online(self) -> bool:
        return self._online

    @property
    def unique_id(self):
        return f"{self._name}_{self._serial_no}"

    @property
    def target_temperature(self):
        config_key = MODE_TO_CONFIG.get(self.operating_mode)
        if config_key is None:
            return None
        return self.get_temperature_from_config(config_key)

    async def set_target_temperature(self, value: float):
        config_key = MODE_TO_CONFIG.get(self.operating_mode)
        if config_key is not None:
            await self.set_config(config_key, int(value * 10))

    def get_status_value(self, idx: int):
        return self._data.get_status_value(idx)

    def get_config_value(self, idx: int):
        return self._data.get_config_value(idx)

    def get_signed_status_value(self, idx: int):
        return self._data.get_signed_status_value(idx)

    def get_signed_config_value(self, idx: int):
        return self._data.get_signed_config_value(idx)

    def get_temperature_from_status(self, idx):
        return self._data.get_status_temperature_value(idx)

    def get_temperature_from_config(self, idx):
        return self._data.get_config_temperature_value(idx)

    @property
    def water_in_temperature(self):
        return self.get_temperature_from_status(16)

    @property
    def operating_mode(self):
        return self._data.get_config_value(4) & 3

    @property
    def is_power_on(self):
        return self._data.get_config_value(4) & 32 == 32

    @property
    def power_mode(self):
        return self._data.get_config_value(16)

    @property
    def dev_type(self):
        """Device type from status register (see DEV_TYPE_* in const.py)."""
        return self.get_status_value(DEV_TYPE_STATUS_IDX)

    @property
    def is_freq_type(self):
        """True if the device is variable-frequency (different max heat temp)."""
        return self.dev_type in (DEV_TYPE_FREQALL, DEV_TYPE_FREQCH)

    @property
    def errors(self):
        errors = []
        for reg, alarm_map in [(48, ALARM_REGISTER_48), (49, ALARM_REGISTER_49), (50, ALARM_REGISTER_50)]:
            value = self.get_status_value(reg)
            for bit, description in alarm_map.items():
                if value & bit:
                    errors.append(description)
        return "\n".join(errors)

    async def set_power_off(self):
        async with self._config4_lock:
            await self.set_config(4, self._data.get_config_value(4) & 0xFFDF)

    async def set_power_on(self):
        async with self._config4_lock:
            await self.set_config(4, self._data.get_config_value(4) | 0x0020)

    async def set_cooling_mode(self):
        async with self._config4_lock:
            await self.set_config(4, (self._data.get_config_value(4) & 0xFFDC) + 32)

    async def set_heating_mode(self):
        async with self._config4_lock:
            await self.set_config(4, (self._data.get_config_value(4) & 0xFFDC) + 33)

    async def set_auto_mode(self):
        async with self._config4_lock:
            await self.set_config(4, (self._data.get_config_value(4) & 0xFFDC) + 34)

    async def set_power_mode(self, value: int):
        await self.set_config(16, value)

    # --- register-4 bit toggles (timer enables, pump run mode) -----------------
    # config_sys1 bit layout (from the official Android app's ControlApi):
    #   bit 0-1: mode (0=cool, 1=heat, 2=auto) — set via set_*_mode
    #   bit 2  : timer-on enable
    #   bit 3  : pump run mode (continuous vs cycling)
    #   bit 5  : power on/off — set via set_power_on/off
    #   bit 6  : debug mode (intentionally not exposed)
    #   bit 7  : timer-off enable

    async def _toggle_config4_bit(self, mask: int, enabled: bool):
        async with self._config4_lock:
            current = self._data.get_config_value(4)
            new = (current | mask) if enabled else (current & (~mask & 0xFFFF))
            await self.set_config(4, new)

    @property
    def is_timer_on_enabled(self) -> bool:
        return bool(self._data.get_config_value(4) & 0x04)

    async def set_timer_on_enabled(self, enabled: bool):
        await self._toggle_config4_bit(0x04, enabled)

    @property
    def is_timer_off_enabled(self) -> bool:
        return bool(self._data.get_config_value(4) & 0x80)

    async def set_timer_off_enabled(self, enabled: bool):
        await self._toggle_config4_bit(0x80, enabled)

    @property
    def is_pump_run_mode_enabled(self) -> bool:
        return bool(self._data.get_config_value(4) & 0x08)

    async def set_pump_run_mode_enabled(self, enabled: bool):
        await self._toggle_config4_bit(0x08, enabled)

    # --- timer on/off time (idx 33/34) ----------------------------------------
    # Encoded as (hour << 8) | minute. The current_time status register (idx 32)
    # uses the same encoding.

    @staticmethod
    def _decode_hhmm(raw: int) -> tuple[int, int]:
        return (raw >> 8) & 0xff, raw & 0xff

    @property
    def timer_on_hhmm(self) -> tuple[int, int]:
        return self._decode_hhmm(self._data.get_config_value(33))

    @property
    def timer_off_hhmm(self) -> tuple[int, int]:
        return self._decode_hhmm(self._data.get_config_value(34))

    async def set_timer_on_hhmm(self, hour: int, minute: int):
        await self.set_config(33, (hour << 8) | (minute & 0xff))

    async def set_timer_off_hhmm(self, hour: int, minute: int):
        await self.set_config(34, (hour << 8) | (minute & 0xff))

    # --- defrost + water compensation -----------------------------------------
    # Bounds from the app (HtcHpParamActivity / TbParamItem):
    #   defrost in temp  (idx  9): -30..0 °C    (raw × 10)
    #   defrost out temp (idx 10):   2..30 °C   (raw × 10)
    #   defrost in time  (idx 12):  30..90 min  (raw)
    #   defrost out time (idx 13):   1..12 min  (raw)
    #   water comp       (idx 11): -9..9 °C     (raw tenths-of-°C, step 0.1)

    @property
    def defrost_in_temp(self) -> float:
        return self._data.get_config_temperature_value(9)

    @property
    def defrost_out_temp(self) -> float:
        return self._data.get_config_temperature_value(10)

    @property
    def water_compensation(self) -> float:
        return self._data.get_signed_config_value(11) / 10.0

    @property
    def defrost_in_time(self) -> int:
        return self._data.get_config_value(12)

    @property
    def defrost_out_time(self) -> int:
        return self._data.get_config_value(13)

    async def set_defrost_in_temp(self, value_c: float):
        await self.set_config(9, int(value_c * 10))

    async def set_defrost_out_temp(self, value_c: float):
        await self.set_config(10, int(value_c * 10))

    async def set_water_compensation(self, value_c: float):
        await self.set_config(11, int(value_c * 10))

    async def set_defrost_in_time(self, minutes: int):
        await self.set_config(12, int(minutes))

    async def set_defrost_out_time(self, minutes: int):
        await self.set_config(13, int(minutes))

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
        packed_data = struct.pack('!BBBBIQ', self.act1, self.act2, self.act3, self.act4, self.clientToken, self.pumpSerial) + packed_uuid + self.timestamp.pack()
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
        if idx - self.startIdx < 0 or idx - self.startIdx >= len(self.data):
            return 0
        return self.data[idx - self.startIdx]

    @staticmethod
    def unpack(data):
        unpacked_data = struct.unpack('!IHHHH', data[0:12])
        obj = Payload(unpacked_data[0], unpacked_data[1], unpacked_data[2], unpacked_data[3], unpacked_data[4])
        if obj.subType == 1 or obj.subType == 2:
            if len(data) < 12 + obj.size:
                raise ValueError(f"Truncated payload: got {len(data)} bytes, need {12 + obj.size}")
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
        self.__status = None
        self.__config = None

    @property
    def is_valid(self):
        return self.__status is not None and self.__config is not None

    def get_status_value(self, idx: int):
        if self.__status is None:
            return 0
        return self.__status.get_value(idx)

    def get_config_value(self, idx: int):
        if self.__config is None:
            return 0
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

        while idx < len(data):
            try:
                payload = Payload.unpack(data[idx:])
            except (ValueError, struct.error) as e:
                _LOGGER.debug("Stopping payload parse early: %s", e)
                break
            if payload.subType == 1:
                obj.__status = payload
            elif payload.subType == 2:
                obj.__config = payload
            idx += payload.size + 8

        return obj


def md5_hash(text):
    """ Simple hashing of password """
    md5 = hashlib.md5()
    md5.update(text.encode())
    return md5.digest()


class AlsavoSocketCom:
    """ Socket communication handler for the Alsavo Pro integration.

    Holds a long-lived auth session (CSID/DSID) across calls. The pump
    accepts re-used CSID/DSID until it times the session out, at which
    point any subsequent packet is dropped with a session-id mismatch
    and the caller is expected to re-auth. We re-auth lazily on the next
    failure rather than running a keep-alive timer."""

    def __init__(self):
        self.serverToken = None
        self.DSIS = None
        self.CSID = None
        self.password = None
        self.serialQ = None
        self.clientToken = None
        self.client = None

    @property
    def is_connected(self) -> bool:
        return self.CSID is not None and self.DSIS is not None and self.client is not None

    def disconnect(self):
        """Drop session state so the next operation re-auths from scratch."""
        self.CSID = None
        self.DSIS = None
        self.serverToken = None
        self.clientToken = None
        self.client = None

    async def send_and_receive(self, bytes_to_send):
        _LOGGER.debug("send_and_receive()")
        response = await self.client.send_rcv(bytes_to_send)
        _LOGGER.debug("Received response")
        return response

    async def get_auth_challenge(self):
        auth_intro = AuthIntro(self.clientToken, self.serialQ)
        response = await self.send_and_receive(bytes(auth_intro.pack()))
        if response is None:
            raise ConnectionError("No response to auth challenge (timeout)")
        return AuthChallenge.unpack(response[0])

    async def send_auth_response(self, ctx):
        resp = AuthResponse(self.CSID, self.DSIS, ctx.digest())
        return await self.send_and_receive(resp.pack())

    async def send_and_rcv_packet(self, payload: bytes, cmd=0xf4):
        _LOGGER.debug("send_and_rcv_packet(payload, %s)", cmd)
        if self.CSID is not None and self.DSIS is not None:
            return await self.send_and_receive(
                PacketHeader(0x32, 0, self.CSID, self.DSIS, cmd, len(payload)).pack() + payload
            )
        return None

    async def query_all(self):
        """ Query all information from the heat pump """
        _LOGGER.debug("socket.query_all")
        resp = await self.send_and_rcv_packet(b'\x08\x01\x00\x00\x00\x02\x00\x2e\xff\xff\x00\x00')
        if resp is None:
            raise ConnectionError("query_all: no response")
        result = QueryResponse.unpack(resp[0][16:])
        if not result.is_valid:
            raise ConnectionError("query_all: response missing status or config section (unexpected packet?)")
        return result

    async def set_config(self, idx: int, value: int):
        """ Set configuration values on the heat pump """
        _LOGGER.debug("socket.set_config(%s, %s)", idx, value)
        idx_h = ((idx >> 8) & 0xff).to_bytes(1, 'big')
        idx_l = (idx & 0xff).to_bytes(1, 'big')
        val_h = ((value >> 8) & 0xff).to_bytes(1, 'big')
        val_l = (value & 0xff).to_bytes(1, 'big')
        # Wait for the pump's write-ACK so we know the command landed before
        # the caller schedules a follow-up poll.
        await self.send_and_rcv_packet(b'\x09\x01\x00\x00\x00\x02\x00\x2e\x00\x02\x00\x04' + idx_h + idx_l + val_h + val_l)

    async def connect(self, server_ip, server_port, serial, password):
        if self.is_connected:
            return
        _LOGGER.debug("Connecting to Alsavo Pro")
        try:
            await self._do_handshake(server_ip, server_port, serial, password)
        except Exception:
            # Avoid leaving partial CSID/DSID/client state that would make
            # is_connected wrongly return True on the next call.
            self.disconnect()
            raise

    async def _do_handshake(self, server_ip, server_port, serial, password):
        self.clientToken = secrets.randbelow(65536)
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

        _LOGGER.debug(
            "Received handshake, CSID=%s, DSID=%s, server token %s",
            hex(self.CSID), hex(self.DSIS), hex(self.serverToken),
        )

        ctx = hashlib.md5()
        ctx.update(self.clientToken.to_bytes(4, "big"))
        ctx.update(self.serverToken.to_bytes(4, "big"))
        ctx.update(md5_hash(self.password))

        response = await self.send_auth_response(ctx)

        if response is None or len(response[0]) == 0:
            raise ConnectionError("Server not responding to auth response, disconnecting.")

        act = int.from_bytes(response[0][16:20], byteorder='little')
        if act != 0x00000005:
            raise ConnectionError("Server returned error in auth, disconnecting")

        _LOGGER.debug("Connected.")
