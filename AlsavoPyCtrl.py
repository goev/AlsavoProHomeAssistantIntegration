import hashlib
import logging
import socket
import struct
from datetime import datetime, timezone, timedelta
from enum import Enum

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
        self._prev_request = datetime.now()

        try:
            self._session = AlsavoSocketCom()
            self._session.connect(self._ip_address, int(self._port_no), int(self._serial_no), self._password)
            if self._session.connectionStatus == ConnectionStatus.Disconnected:
                raise Exception("Unable to connect to heater.")

            self._data = self._session.queryAll()
            self._session.Disconnect()
        except Exception as e:
            _LOGGER.error(f"Something went wrong: {e}")
            if self._session is not None:
                self._session.Disconnect()
            self._data = QueryResponse(0, 0)

    async def update(self):
        try:
            # Only update if more than 10 seconds since last update
            if self._data.parts > 0 and abs(self._prev_request - datetime.now()) < timedelta(seconds=10):
                return

            self._session = AlsavoSocketCom()
            self._session.connect(self._ip_address, int(self._port_no), int(self._serial_no), self._password)
            if self._session.connectionStatus == ConnectionStatus.Connected:
                self._data = self._session.queryAll()
                self._prev_request = datetime.now()
        except Exception as e:
            _LOGGER.error(f"Unable to connect to heatpump {e}")
            if self._session is not None:
                self._session.Disconnect()
            self._data = QueryResponse(0, 0)

        # timeout = 10
        # try:
        #     async with async_timeout.timeout(timeout):
        #         session = await get_session(self._serial_no, self._ip_address, self._port_no, self._password)
        #         if session == None: raise Exception("Could not get session.")
        #         self._data = session.queryAll()
        #         session.Disconnect()
        # except asyncio.TimeoutError:
        #     _LOGGER.error("Timed out when refreshing to Alsavo Pro pool heater")
        # except Exception as err:
        #     _LOGGER.error("Error refreshing Alsavo Pro: %s ", err, exc_info=True)

    def isOnline(self)->bool:
        return self._data.parts > 0

    def uniqueId(self):
        return f"{self._name}_{self._serial_no}"

    def getTargetTemperature(self):
        if self.getOperatingMode() == 0: #Cool
            return self.getTemperatureFromConfig(2)
        elif self.getOperatingMode() == 1: #Heat
            return self.getTemperatureFromConfig(1)
        elif self.getOperatingMode() == 2: #Auto
            return self.getTemperatureFromConfig(3)
        return 0

    def setTargetTemperature(self, value: float):
        if self.getOperatingMode() == 0: #Cool
            self.setConfig(2, int(value * 10))
        elif self.getOperatingMode() == 1: #Heat
            self.setConfig(1, int(value * 10))
        elif self.getOperatingMode() == 2: #Auto
            self.setConfig(3, int(value * 10))

    def getStatusValue(self,idx: int):
        return self._data.getStatusValue(idx)

    def getConfigValue(self,idx: int):
        return self._data.getConfigValue(idx)

    def getTemperatureFromStatus(self, idx):
        return self._data.getStatusTemperatureValue(idx)
    def getTemperatureFromConfig(self, idx):
        return self._data.getConfigTemperatureValue(idx)
    def getWaterInTemperature(self):
        return self.getTemperatureFromStatus(16)

    def getWaterOutTemperature(self):
        return self.getTemperatureFromStatus(17)

    def getAmbientTemperature(self):
        return self.getTemperatureFromStatus(18)

    def getOperatingMode(self):
        return self._data.getConfigValue(4) & 3

    def getTimerOnEnabled(self):
        return self._data.getConfigValue(4) & 4 == 4

    def getWaterPumpRunningMode(self):
        return self._data.getConfigValue(4) & 8 == 8

    def getElectronicValveStyle(self):
        return self._data.getConfigValue(4) & 16 == 16

    def isPowerOn(self):
        return self._data.getConfigValue(4) & 32 == 32

    def setPowerOff(self):
        self.setConfig(4, self._data.getConfigValue(4) & 0xFFDF)

    def setCoolingMode(self):
        self.setConfig(4, (self._data.getConfigValue(4) & 0xFFDC) + 32)

    def setHeatingMode(self):
        self.setConfig(4, (self._data.getConfigValue(4) & 0xFFDC) + 33)

    def setAutoMode(self):
        self.setConfig(4, (self._data.getConfigValue(4) & 0xFFDC) + 34)

    def getPowerMode(self):
        return self._data.getConfigValue(16)

    def setPowerMode(self,value: int):
        self.setConfig(16, value)

    def getDebugMode(self):
        return self._data.getConfigValue(4) & 64 == 64

    def getTimerOffEnabled(self):
        return self._data.getConfigValue(4) & 128 == 128

    def getManualDefrost(self):
        return self._data.getConfigValue(5) & 1 == 1

    def setConfig(self, idx: int, value: int):
        try:
            self._session = AlsavoSocketCom()
            self._session.connect(self._ip_address, int(self._port_no), int(self._serial_no), self._password)
            if self._session.connectionStatus == ConnectionStatus.Disconnected:
                raise Exception("Unable to connect to heater.")
            self._session.setConfig(idx, value)
        except Exception as e:
            _LOGGER.error(f"Something went wrong: {e}")

        if self._session is not None:
            self._session.Disconnect()

    def getErrors(self):
        error = ""
        if(self.getStatusValue(48) & 0x4 == 0x4):
            error += "No water flux or water flow switch failure.\n\r"
        if(self.getStatusValue(49) & 0x400 == 0x400):
            error += "Water temperature (T2) too low protection under cooling mode.\n\r"
        return error

""" Header for all packets """
class PacketHeader:
    ''' This is the packet header
    It is 16 bytes long and have the following attributes:
    - hdr - byte - 0x32 = request, 0x30 = response
    - pad - byte - Padding. Always 0
    - seq - Int16 - Sequence number (monotonically increasing once session has been set up, otherwise 0)
    - csid - Int32 -
    '''

    def __init__(self, hdr, seq, csid, dsid, cmd, payloadLength):
        self.hdr = hdr
        self.pad = 0
        self.seq = seq
        self.csid = csid
        self.dsid = dsid
        self.cmd = cmd
        self.payloadLength = payloadLength

    def isReply(self):
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
        self.now()

    def now(self):
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
    def __init__(self, clientToken, serialInv):
        self.hdr = PacketHeader(0x32, 0, 0, 0, 0xf2, 0x28)
        self.act1, self.act2, self.act3, self.act4 = 1, 1, 2, 0
        self.clientToken = clientToken
        self.pumpSerial = serialInv
        # self._uuid = [0xffffffff, 0xd3e2eeac, 0, 0x6afdc755]
        self._uuid = [0x97e8ced0, 0xf83640bc, 0xb4dd57e3, 0x22adc3a0]
        self.timestamp = Timestamp()

    def pack(self):
        packed_hdr = self.hdr.pack()
        packed_uuid = struct.pack('!IIII', *self._uuid)
        packed_data = struct.pack('!BBBBIQ', self.act1, self.act2, self.act3, self.act4, self.clientToken,
                                  self.pumpSerial) + packed_uuid + self.timestamp.pack()
        return packed_hdr + packed_data

class AuthChallenge:
    def __init__(self, hdr, act1, act2, act3, act4, serverToken):
        self.hdr = hdr
        self.act1 = act1
        self.act2 = act2
        self.act3 = act3
        self.act4 = act4
        self.serverToken = serverToken

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
    def isAuthorized(self):
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

""" Config, Status or device info-payload packet """
class Payload:
    def __init__(self, type, subType, size, startIdx, indices):
        self.type = type
        self.subType = subType
        self.size = size
        self.startIdx = startIdx
        self.indices = indices
        self.data = []

    def getValue(self, idx):
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

""" Query response containing data payload from heatpump. """
""" Contains both status and config. """
class QueryResponse:
    def __init__(self, action, parts):
        self.action = action
        self.parts = parts
        self.__payloads = []
        self.__status = None
        self.__config = None
        self.__deviceInfo = None

    def getStatusValue(self, idx: int):
        if self.__status is None:
            return 0
        else:
            return self.__status.getValue(idx)

    def getConfigValue(self, idx: int):
        if self.__config is None:
            return 0
        else:
            return self.__config.getValue(idx)

    def getStatusTemperatureValue(self, idx: int):
        return self.getStatusValue(idx) / 10

    def getConfigTemperatureValue(self, idx: int):
        return self.getConfigValue(idx) / 10

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

""" Simple hashing of password """
def Hash(text):
    md5 = hashlib.md5()
    md5.update(text.encode())
    return md5.digest()

class ConnectionStatus(Enum):
    Disconnected = 0
    Connected = 1

""" Socket communcation handler for the Alsavo Pro integration """
""" Everything is pull-based. """
class AlsavoSocketCom:
    def __init__(self):
        self.connectionStatus = ConnectionStatus.Disconnected
        self.lastPacketRcvTime = datetime.now()

    def UpdateConnectionStatus(self, status):
        if isinstance(status, ConnectionStatus):
            self.connectionStatus = status
        else:
            raise ValueError("Illegal connection status")

    def send(self, bytesToSend):
        self.m_Sock.sendto(bytesToSend, self.serverAddressPort)
        return self.m_Sock.recvfrom(1024)

    def rvc(self):
        return self.m_Sock.recvfrom(1024)

    def createSocket(self, serverIP, serverPort):
        self.serverAddressPort = (serverIP, serverPort)
        self.m_Sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.m_Sock.settimeout(3)

    def getAuthChallenge(self, auth_intro: AuthIntro):
        response = self.send(bytes(auth_intro.pack()))
        return AuthChallenge.unpack(response[0])

    def sendAuthResponse(self, resp: AuthResponse):
        return self.send(resp.pack())

    def SendPacket(self, payload: bytes, cmd=0xf4):
        return self.send(PacketHeader(0x32, 0, self.m_CSID, self.m_DSIS, cmd, payload.__len__()).pack() + payload)

    def queryAll(self):
        resp = self.SendPacket(b'\x08\x01\x00\x00\x00\x02\x00\x2e\xff\xff\x00\x00')
        self.lstConfigReqTime = datetime.now()
        return QueryResponse.unpack(resp[0][16:])

    def setConfig(self,idx: int, value: int):
        idxH = ((idx >> 8) & 0xff).to_bytes(1,'big')
        idxL = (idx & 0xff).to_bytes(1,'big')
        valH = ((value >> 8) & 0xff).to_bytes(1,'big')
        valL = (value & 0xff).to_bytes(1,'big')
        self.SendPacket(b'\x09\x01\x00\x00\x00\x02\x00\x2e\x00\x02\x00\x04'+idxH+idxL+valH+valL)

    def connect(self, serverIP, serverPort, serial, password):
        _LOGGER.debug("Connection to Alsavo Pro")

        self.m_ClientToken = 3112
        self.m_SerialQ = serial
        self.m_Password = password

        auth_intro = AuthIntro(self.m_ClientToken, self.m_SerialQ)

        self.createSocket(serverIP, serverPort)

        # Create a UDP socket at client side
        _LOGGER.debug("Asking for auth challenge")
        auth_challenge = self.getAuthChallenge(auth_intro)

        if not auth_challenge.isAuthorized:
            _LOGGER.error("Invalid auth challenge packet (pump offline?), disconnecting", exc_info=True)
            self.Disconnect()
            return

        self.m_CSID = auth_challenge.hdr.csid
        self.m_DSIS = auth_challenge.hdr.dsid
        self.m_ServerToken = auth_challenge.serverToken

        _LOGGER.debug(f"Received handshake, CSID={hex(self.m_CSID)}, DSID={hex(self.m_DSIS)}, server token {hex(self.m_ServerToken)}")

        ctx = hashlib.md5()
        ctx.update(self.m_ClientToken.to_bytes(4, "big"))
        ctx.update(self.m_ServerToken.to_bytes(4, "big"))
        ctx.update(Hash(self.m_Password))

        resp = AuthResponse(self.m_CSID, self.m_DSIS, ctx.digest())
        response = self.sendAuthResponse(resp)

        if response[0].__len__() == 0:
            _LOGGER.error("Server not responding to auth response, disconnecting.")
            self.Disconnect()
            return

        act = int.from_bytes(response[0][16:20], byteorder='little')
        if act != 0x00000005:
            _LOGGER.error("Server returned error in auth, disconnecting")
            self.Disconnect()
            return

        self.lastPacketRcvTime = datetime.now();
        self.UpdateConnectionStatus(ConnectionStatus.Connected)

        _LOGGER.debug("Connection complete.")

    def Disconnect(self):
        _LOGGER.debug("Disconnecting")
        try:
            self.UpdateConnectionStatus(ConnectionStatus.Connected)
            self.m_NextSeq = 0
            self.m_Sock.close()
        except Exception as e:
            _LOGGER.error(f"Disconnecting failed {e}")

