"""Module to interact with your Panasonic Viera TV."""
from enum import Enum
import logging
import random
import socket
import base64
import struct
import hmac
import hashlib
from http import HTTPStatus
import re
import asyncio
from xml.etree import ElementTree
import aiohttp.web
import xmltodict
from Crypto.Cipher import AES

try:
    from urllib.request import urlopen, Request, HTTPError, build_opener, HTTPHandler
except ImportError:
    from urllib2 import urlopen, Request, HTTPError, build_opener, HTTPHandler

_LOGGER = logging.getLogger(__name__)

URN_RENDERING_CONTROL = "schemas-upnp-org:service:RenderingControl:1"
URN_REMOTE_CONTROL = "panasonic-com:service:p00NetworkControl:1"

URL_TEMPLATE = "http://{}:{}/{}"

URL_CONTROL_NRC_DDD = "nrc/ddd.xml"
URL_CONTROL_NRC_DEF = "nrc/sdd_0.xml"

URL_CONTROL_DMR = "dmr/control_0"
URL_CONTROL_NRC = "nrc/control_0"

TV_TYPE_NONENCRYPTED = 0
TV_TYPE_ENCRYPTED = 1

DEFAULT_PORT = 55000

BLOCK_SIZE = 16  # Bytes


def pad(s):
    return s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(0)


class Keys(Enum):
    """Contains all known keys."""

    THIRTY_SECOND_SKIP = "NRC_30S_SKIP-ONOFF"
    TOGGLE_3D = "NRC_3D-ONOFF"
    APPS = "NRC_APPS-ONOFF"
    ASPECT = "NRC_ASPECT-ONOFF"
    BACK = "NRC_RETURN-ONOFF"
    BLUE = "NRC_BLUE-ONOFF"
    CANCEL = "NRC_CANCEL-ONOFF"
    CC = "NRC_CC-ONOFF"
    CHAT_MODE = "NRC_CHAT_MODE-ONOFF"
    CH_DOWN = "NRC_CH_DOWN-ONOFF"
    INPUT_KEY = "NRC_CHG_INPUT-ONOFF"
    NETWORK = "NRC_CHG_NETWORK-ONOFF"
    CH_UP = "NRC_CH_UP-ONOFF"
    NUM_0 = "NRC_D0-ONOFF"
    NUM_1 = "NRC_D1-ONOFF"
    NUM_2 = "NRC_D2-ONOFF"
    NUM_3 = "NRC_D3-ONOFF"
    NUM_4 = "NRC_D4-ONOFF"
    NUM_5 = "NRC_D5-ONOFF"
    NUM_6 = "NRC_D6-ONOFF"
    NUM_7 = "NRC_D7-ONOFF"
    NUM_8 = "NRC_D8-ONOFF"
    NUM_9 = "NRC_D9-ONOFF"
    DIGA_CONTROL = "NRC_DIGA_CTL-ONOFF"
    DISPLAY = "NRC_DISP_MODE-ONOFF"
    DOWN = "NRC_DOWN-ONOFF"
    ENTER = "NRC_ENTER-ONOFF"
    EPG = "NRC_EPG-ONOFF"
    EXIT = "NRC_CANCEL-ONOFF"
    EZ_SYNC = "NRC_EZ_SYNC-ONOFF"
    FAVORITE = "NRC_FAVORITE-ONOFF"
    FAST_FORWARD = "NRC_FF-ONOFF"
    GAME = "NRC_GAME-ONOFF"
    GREEN = "NRC_GREEN-ONOFF"
    GUIDE = "NRC_GUIDE-ONOFF"
    HOLD = "NRC_HOLD-ONOFF"
    HOME = "NRC_HOME-ONOFF"
    INDEX = "NRC_INDEX-ONOFF"
    INFO = "NRC_INFO-ONOFF"
    CONNECT = "NRC_INTERNET-ONOFF"
    LEFT = "NRC_LEFT-ONOFF"
    MENU = "NRC_MENU-ONOFF"
    MPX = "NRC_MPX-ONOFF"
    MUTE = "NRC_MUTE-ONOFF"
    NET_BS = "NRC_NET_BS-ONOFF"
    NET_CS = "NRC_NET_CS-ONOFF"
    NET_TD = "NRC_NET_TD-ONOFF"
    OFF_TIMER = "NRC_OFFTIMER-ONOFF"
    PAUSE = "NRC_PAUSE-ONOFF"
    PICTAI = "NRC_PICTAI-ONOFF"
    PLAY = "NRC_PLAY-ONOFF"
    P_NR = "NRC_P_NR-ONOFF"
    POWER = "NRC_POWER-ONOFF"
    PROGRAM = "NRC_PROG-ONOFF"
    RECORD = "NRC_REC-ONOFF"
    RED = "NRC_RED-ONOFF"
    RETURN_KEY = "NRC_RETURN-ONOFF"
    REWIND = "NRC_REW-ONOFF"
    RIGHT = "NRC_RIGHT-ONOFF"
    R_SCREEN = "NRC_R_SCREEN-ONOFF"
    LAST_VIEW = "NRC_R_TUNE-ONOFF"
    SAP = "NRC_SAP-ONOFF"
    TOGGLE_SD_CARD = "NRC_SD_CARD-ONOFF"
    SKIP_NEXT = "NRC_SKIP_NEXT-ONOFF"
    SKIP_PREV = "NRC_SKIP_PREV-ONOFF"
    SPLIT = "NRC_SPLIT-ONOFF"
    STOP = "NRC_STOP-ONOFF"
    SUBTITLES = "NRC_STTL-ONOFF"
    OPTION = "NRC_SUBMENU-ONOFF"
    SURROUND = "NRC_SURROUND-ONOFF"
    SWAP = "NRC_SWAP-ONOFF"
    TEXT = "NRC_TEXT-ONOFF"
    TV = "NRC_TV-ONOFF"
    UP = "NRC_UP-ONOFF"
    LINK = "NRC_VIERA_LINK-ONOFF"
    VOLUME_DOWN = "NRC_VOLDOWN-ONOFF"
    VOLUME_UP = "NRC_VOLUP-ONOFF"
    VTOOLS = "NRC_VTOOLS-ONOFF"
    YELLOW = "NRC_YELLOW-ONOFF"
    HMDI_1 = "NRC_HDMI1-ONOFF"
    HMDI_2 = "NRC_HDMI2-ONOFF"
    HMDI_3 = "NRC_HDMI3-ONOFF"
    HMDI_4 = "NRC_HDMI4-ONOFF"


class Apps(Enum):
    """Contains several app product IDs."""

    NETFLIX = "0010000200000001"
    YOUTUBE = "0070000200180001"
    SHOUTCAST = "0070000400000001"
    CALENDAR = "0387878700150020"
    BROWSER = "0077777700160002"
    AMAZONPRIME = "0010000100180001"
    IPLAYER = "0020000A00000010"
    BBCIPLAYER = "0020000A00000010"
    ITV = "0387878700000124"
    ALL4 = "0387878700000125"
    DEMAND5 = "0020009300000001"
    RECORDEDTV = "0387878700000013"
    MULTIWINDOW = "0387878700000050"
    BBCNEWS = "0020000A00000006"
    BBCSPORT = "0020000A00000007"
    WEATHER = "0070000C00000001"
    DEVELOPER = "0077777777777778"


class SOAPError(Exception):
    """This exception is thrown when a SOAP error happens."""


class EncryptionRequired(Exception):
    """This exception is thrown when encryption is required."""


class RemoteControl:
    """This class represents a Panasonic Viera TV Remote Control."""

    def __init__(
        self,
        host,
        port=DEFAULT_PORT,
        app_id=None,
        encryption_key=None,
        listen_host=None,
        listen_port=DEFAULT_PORT,
    ):
        """Initialise the remote control."""
        self._host = host
        self._port = port
        self._app_id = app_id
        self._enc_key = encryption_key
        self._listen_host = listen_host
        self._listen_port = listen_port
        self._session_key = None
        self._session_iv = None
        self._session_id = None
        self._session_seq_num = None
        self._session_hmac_key = None

        self._service_to_sid = {}
        self._sid_to_service = {}

        self._aiohttp_server = None
        self._server = None

        if self._app_id is None or self._enc_key is None:
            self._type = TV_TYPE_NONENCRYPTED
        else:
            self._type = TV_TYPE_ENCRYPTED
            self._derive_session_keys()
            self._request_session_id()

        # Determine if the TV uses encryption or not
        if self._type == TV_TYPE_NONENCRYPTED:
            url = URL_TEMPLATE.format(self._host, self._port, URL_CONTROL_NRC_DEF)

            _LOGGER.debug("Determining TV type\n")
            res = urlopen(url, timeout=5).read()
            root = ElementTree.fromstring(res)
            for child in root:
                if child.tag.endswith("actionList"):
                    for subchild in child.iter():
                        if (
                            subchild.tag.endswith("name")
                            and subchild.text == "X_GetEncryptSessionId"
                        ):
                            self._type = TV_TYPE_ENCRYPTED
            tv_enc_type = (
                "encrypted" if self._type == TV_TYPE_ENCRYPTED else "non-encrypted"
            )
            _LOGGER.debug("Determined TV type is %s\n", tv_enc_type)

    def soap_request(self, url, urn, action, params, body_elem="m"):
        """Send a SOAP request to the TV."""

        is_encrypted = False

        # Encapsulate URN_REMOTE_CONTROL command in an X_EncryptedCommand if we're using encryption
        if urn == URN_REMOTE_CONTROL and action not in [
            "X_GetEncryptSessionId",
            "X_DisplayPinCode",
            "X_RequestAuth",
        ]:
            if None not in [
                self._session_key,
                self._session_iv,
                self._session_hmac_key,
                self._session_id,
                self._session_seq_num,
            ]:
                is_encrypted = True
                self._session_seq_num += 1
                body_elem = "u"
                encrypted_command = (
                    f"<X_SessionId>{self._session_id}</X_SessionId>"
                    f"<X_SequenceNumber>{self._session_seq_num:08d}</X_SequenceNumber>"
                    "<X_OriginalCommand>"
                    f'<{body_elem}:{action} xmlns:{body_elem}="urn:{urn}">'
                    f"{params}"
                    f"</{body_elem}:{action}>"
                    "</X_OriginalCommand>"
                )

                encrypted_command = self._encrypt_soap_payload(
                    encrypted_command,
                    self._session_key,
                    self._session_iv,
                    self._session_hmac_key,
                )

                action = "X_EncryptedCommand"
                params = (
                    f"<X_ApplicationId>{self._app_id}</X_ApplicationId>"
                    f"<X_EncInfo>{encrypted_command}</X_EncInfo>"
                )
                body_elem = "u"
            elif self._type == TV_TYPE_ENCRYPTED:
                raise EncryptionRequired(
                    "Please refer to the docs for using encryption"
                )

        # Construct SOAP request
        soap_body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"'
            ' s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            "<s:Body>"
            f'<{body_elem}:{action} xmlns:{body_elem}="urn:{urn}">'
            f"{params}"
            f"</{body_elem}:{action}>"
            "</s:Body>"
            "</s:Envelope>"
        ).encode("utf-8")

        headers = {
            "Host": f"{self._host}:{self._port}",
            "Content-Length": len(soap_body),
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"urn:{urn}#{action}"',
        }

        url = URL_TEMPLATE.format(self._host, self._port, url)

        _LOGGER.debug("Sending to %s:\n%s\n%s", url, headers, soap_body)
        req = Request(url, soap_body, headers)
        try:
            res = urlopen(req, timeout=5).read()
        except HTTPError as ex:
            if self._session_seq_num is not None:
                self._session_seq_num -= 1
            raise ex  # Pass to the next handler
        _LOGGER.debug("Response: %s", res)

        if is_encrypted:
            root = ElementTree.fromstring(res)
            enc_result = root.find(".//X_EncResult").text
            enc_result_decrypted = self._decrypt_soap_payload(
                enc_result, self._session_key, self._session_iv, self._session_hmac_key
            )
            res = enc_result_decrypted

        return res

    def _derive_session_keys(self):
        init_vector = bytearray(base64.b64decode(self._enc_key))

        self._session_iv = init_vector

        # Get character codes from IV bytes
        iv_vals = [c for c in init_vector]

        # Initialise key character codes array
        key_vals = [0] * 16

        # Derive key from IV
        i = 0
        while i < 16:
            key_vals[i] = iv_vals[i + 2]
            key_vals[i + 1] = iv_vals[i + 3]
            key_vals[i + 2] = iv_vals[i]
            key_vals[i + 3] = iv_vals[i + 1]
            i += 4

        # Convert our key character codes to bytes
        # self._session_key = ''.join(chr(c) for c in key_vals)
        self._session_key = bytearray(c for c in key_vals)

        # HMAC key for comms is just the IV repeated twice
        self._session_hmac_key = init_vector * 2

    def _encrypt_soap_payload(self, data, key, init_vector, hmac_key):
        # The encrypted payload must begin with a 16-byte header (12 random bytes, and 4 bytes for
        # the payload length in big endian)
        # Note: the server does not appear to ever send back valid payload lengths in bytes 13-16,
        # so I would assume these can also be randomized by the client, but we'll set them anyway
        # to be safe.
        payload = bytearray(random.randint(0, 255) for _ in range(12))
        payload += struct.pack(">I", len(data))
        payload += data.encode("latin-1")

        # For compatibility with both Python 2.x and 3.x, flattening types to 'str' or 'bytes'
        init_vector = init_vector.decode("latin-1").encode("latin-1")
        key = key.decode("latin-1").encode("latin-1")
        payload = pad(payload.decode("latin-1")).encode("latin-1")
        hmac_key = hmac_key.decode("latin-1").encode("latin-1")

        # Initialize AES-CBC with key and IV
        aes = AES.new(key, AES.MODE_CBC, init_vector)
        # Encrypt with zero-padding
        ciphertext = aes.encrypt(payload)
        # Compute HMAC-SHA-256
        sig = hmac.new(hmac_key, ciphertext, hashlib.sha256).digest()
        # Concat HMAC with AES-encrypted payload
        return base64.b64encode(ciphertext + sig).decode("latin-1")

    def _decrypt_soap_payload(self, data, key, init_vector, hmac_key):
        # For compatibility with both Python 2.x and 3.x, flattening types to 'str' or 'bytes'
        key = key.decode("latin-1").encode("latin-1")
        init_vector = init_vector.decode("latin-1").encode("latin-1")

        # Initialize AES-CBC with key and IV
        aes = AES.new(key, AES.MODE_CBC, init_vector)
        # Decrypt
        decrypted = aes.decrypt(base64.b64decode(data)).decode("latin-1")
        # Unpad and return
        return decrypted[16:].split("\0")[0]

    def request_pin_code(self, name="My Remote"):
        # First let's ask for a pin code and get a challenge key back
        params = "<X_DeviceName>" + name + "</X_DeviceName>"
        try:
            res = self.soap_request(
                URL_CONTROL_NRC,
                URN_REMOTE_CONTROL,
                "X_DisplayPinCode",
                params,
                body_elem="u",
            )
        except HTTPError as ex:
            if ex.code == 500:
                xml = ElementTree.fromstring(ex.fp.read())
                for child in xml.iter():
                    if child.tag.endswith("errorDescription"):
                        raise SOAPError(child.text)
                return
            raise ex  # Pass to the next handler
        root = ElementTree.fromstring(res)
        self._challenge = bytearray(
            base64.b64decode(root.find(".//X_ChallengeKey").text)
        )

    def authorize_pin_code(self, pincode):
        # Second, let's encrypt the pin code using the challenge key and send it back
        # to authenticate

        # Derive key from IV
        init_vector = self._challenge
        key = bytearray([0] * 16)
        i = 0
        while i < 16:
            key[i] = ~init_vector[i + 3] & 0xFF
            key[i + 1] = ~init_vector[i + 2] & 0xFF
            key[i + 2] = ~init_vector[i + 1] & 0xFF
            key[i + 3] = ~init_vector[i] & 0xFF
            i += 4

        # Derive HMAC key from IV & HMAC key mask (taken from libtvconnect.so)
        hmac_key_mask_vals = [
            0x15,
            0xC9,
            0x5A,
            0xC2,
            0xB0,
            0x8A,
            0xA7,
            0xEB,
            0x4E,
            0x22,
            0x8F,
            0x81,
            0x1E,
            0x34,
            0xD0,
            0x4F,
            0xA5,
            0x4B,
            0xA7,
            0xDC,
            0xAC,
            0x98,
            0x79,
            0xFA,
            0x8A,
            0xCD,
            0xA3,
            0xFC,
            0x24,
            0x4F,
            0x38,
            0x54,
        ]
        hmac_key = bytearray([0] * 32)
        i = 0
        while i < 32:
            hmac_key[i] = hmac_key_mask_vals[i] ^ init_vector[(i + 2) & 0xF]
            hmac_key[i + 1] = hmac_key_mask_vals[i + 1] ^ init_vector[(i + 3) & 0xF]
            hmac_key[i + 2] = hmac_key_mask_vals[i + 2] ^ init_vector[i & 0xF]
            hmac_key[i + 3] = hmac_key_mask_vals[i + 3] ^ init_vector[(i + 1) & 0xF]
            i += 4

        # Encrypt X_PinCode argument and send it within an X_AuthInfo tag
        payload = self._encrypt_soap_payload(
            f"<X_PinCode>{pincode}</X_PinCode>", key, init_vector, hmac_key
        )
        params = f"<X_AuthInfo>{payload}</X_AuthInfo>"
        try:
            res = self.soap_request(
                URL_CONTROL_NRC,
                URN_REMOTE_CONTROL,
                "X_RequestAuth",
                params,
                body_elem="u",
            )
        except HTTPError as ex:
            if ex.code == 500:
                xml = ElementTree.fromstring(ex.fp.read())
                for child in xml.iter():
                    if child.tag.endswith("errorCode") and child.text == "600":
                        raise SOAPError("Invalid PIN Code!")
                    elif child.tag.endswith("errorDescription"):
                        raise SOAPError(child.text)
                return
            raise ex  # Pass to the next handler

        # Parse and decrypt X_AuthResult
        root = ElementTree.fromstring(res)
        auth_result = root.find(".//X_AuthResult").text
        payload = self._decrypt_soap_payload(auth_result, key, init_vector, hmac_key)
        auth_result_decrypted = ElementTree.fromstring(f"<X_Data>{payload}</X_Data>")

        # Set session application ID and encryption key
        self._app_id = auth_result_decrypted.find(".//X_ApplicationId").text
        self._enc_key = auth_result_decrypted.find(".//X_Keyword").text

        # Derive AES & HMAC keys from X_Keyword
        self._derive_session_keys()

        # Request a session
        self._request_session_id()

    def _request_session_id(self):
        # Thirdly, let's ask for a session. We'll need to use a valid session ID for encrypted
        # NRC commands.

        # We need to send an encrypted version of X_ApplicationId
        encinfo = self._encrypt_soap_payload(
            "<X_ApplicationId>" + self._app_id + "</X_ApplicationId>",
            self._session_key,
            self._session_iv,
            self._session_hmac_key,
        )

        # Send the encrypted SOAP request along with plaintext X_ApplicationId
        params = (
            f"<X_ApplicationId>{self._app_id}</X_ApplicationId>"
            f"<X_EncInfo>{encinfo}</X_EncInfo>"
        )
        try:
            res = self.soap_request(
                URL_CONTROL_NRC,
                URN_REMOTE_CONTROL,
                "X_GetEncryptSessionId",
                params,
                body_elem="u",
            )
        except HTTPError as ex:
            if ex.code == 500:
                xml = ElementTree.fromstring(ex.fp.read())
                for child in xml.iter():
                    if child.tag.endswith("errorDescription"):
                        raise SOAPError(child.text)
                return
            raise ex  # Pass to the next handler

        root = ElementTree.fromstring(res)
        enc_result = root.find(".//X_EncResult").text
        enc_result_decrypted = ElementTree.fromstring(
            "<X_Data>"
            + self._decrypt_soap_payload(
                enc_result, self._session_key, self._session_iv, self._session_hmac_key
            )
            + "</X_Data>"
        )

        # Set session ID and begin sequence number at 1. We have to increment the sequence number
        # upon each successful NRC command.
        self._session_id = enc_result_decrypted.find(".//X_SessionId").text
        self._session_seq_num = 1

    # Taken from https://github.com/home-assistant/ file: home-assistant/homeassistant/util
    # /__init__.py
    def _get_local_ip(self):
        """Try to determine the local IP address of the machine."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Use Google Public DNS server to determine own IP
            sock.connect(("8.8.8.8", 80))

            return sock.getsockname()[0]
        except socket.error:
            try:
                return socket.gethostbyname(socket.gethostname())
            except socket.gaierror:
                return "127.0.0.1"
        finally:
            sock.close()

    def _do_custom_request(self, method, url, headers=None, timeout=10):
        opener = build_opener(HTTPHandler)
        req = Request(url, headers=headers, method=method)
        res = opener.open(req, timeout=timeout)

        status = res.status
        header = dict(res.info())

        return status, header

    def upnp_service_subscribe(self, service, timeout=10):
        """Subscribe to a UPnP service."""
        headers = {
            "NT": "upnp:event",
            "TIMEOUT": "Second-" + str(timeout),
            "HOST": f"{self._host}:{self._port}",
            "CALLBACK": f"<http://{self._listen_host}:{self._listen_port}/notify>",
        }

        status, headers = self._do_custom_request(
            "SUBSCRIBE",
            f"http://{self._host}:{self._port}/{service}",
            headers=headers,
            timeout=timeout,
        )

        if "SID" in headers and headers["SID"]:
            self._service_to_sid[service] = headers["SID"]
            self._sid_to_service[headers["SID"]] = service

        return status, headers

    def upnp_service_resubscribe(self, service, timeout=10):
        """Renew subscription to a UPnP service."""
        if service not in self._service_to_sid:
            _LOGGER.error("Couldn't renew subscription of service %s", service)
            return

        headers = {
            "HOST": f"{self._host}:{self._port}",
            "SID": self._service_to_sid[service],
            "TIMEOUT": "Second-" + str(timeout),
        }

        status, headers = self._do_custom_request(
            "SUBSCRIBE",
            f"http://{self._host}:{self._port}/{service}",
            headers=headers,
            timeout=timeout,
        )

        if "SID" in headers and headers["SID"]:
            self._service_to_sid[service] = headers["SID"]
            self._sid_to_service[headers["SID"]] = service

        return status, headers

    def upnp_service_unsubscribe(self, service, timeout=10):
        """Unsubscribe from a UPnP service."""
        if service not in self._service_to_sid:
            _LOGGER.debug("Couldn't unsubscribe from service %s", service)
            return

        headers = {
            "HOST": f"{self._host}:{self._port}",
            "SID": self._service_to_sid[service],
            "TIMEOUT": "Second-" + str(timeout),
        }

        status, headers = self._do_custom_request(
            "UNSUBSCRIBE",
            f"http://{self._host}:{self._port}/{service}",
            headers=headers,
            timeout=timeout,
        )

        self._service_to_sid.pop(service)

        return status, headers

    async def async_start_server(self):
        """Start the HTTP server."""
        self._listen_host = self._listen_host or self._get_local_ip()

        _LOGGER.debug("Creating server at %s:%d", self._listen_host, self._listen_port)

        self._aiohttp_server = aiohttp.web.Server(self._handle_request)
        loop = asyncio.get_event_loop()
        try:
            self._server = await loop.create_server(
                self._aiohttp_server, self._listen_host, self._listen_port
            )
        except OSError as error:
            _LOGGER.error(
                "Failed to create HTTP server at %s:%d: %s",
                self._listen_host,
                self._listen_port,
                error,
            )

    async def async_stop_server(self, timeout=10):
        """Stop the HTTP server."""
        _LOGGER.debug("Stopping server")

        if self._aiohttp_server:
            await self._aiohttp_server.shutdown(timeout)

        if self._server:
            self._server.close()

    async def _handle_request(self, request):
        """Handle incoming requests."""
        if request.method != "NOTIFY":
            _LOGGER.debug("Request received is not of method notify")
            return aiohttp.web.Response(status=405)

        headers = request.headers
        body = await request.text()

        if "NT" not in headers or "NTS" not in headers:
            _LOGGER.debug("Sending response: %s", HTTPStatus.BAD_REQUEST)
            return HTTPStatus.BAD_REQUEST

        if (
            headers["NT"] != "upnp:event"
            or headers["NTS"] != "upnp:propchange"
            or "SID" not in headers
        ):
            _LOGGER.debug("Sending response: %s", HTTPStatus.PRECONDITION_FAILED)
            return HTTPStatus.PRECONDITION_FAILED

        sid = headers["SID"]
        service = None
        if sid in self._sid_to_service:
            service = self._sid_to_service[sid]

        body = body.strip().strip("\u0000")
        root = xmltodict.parse(body)
        properties = root["e:propertyset"]["e:property"]

        if "LastChange" in properties:
            last_change = properties["LastChange"]
            properties = xmltodict.parse(last_change)["Event"]["InstanceID"]

        _LOGGER.debug(
            "Received valid request from service %s. Handling properties:",
            service,
        )
        _LOGGER.debug(properties)

        await self.on_event(service, properties)

        return HTTPStatus.OK

    async def on_event(self, service, properties):
        """Parse the received data. This method can be overridden by the user."""
        _LOGGER.info("Please override the on_event method to handle the received data.")

    def get_device_info(self):
        """Retrieve information from the TV."""
        url = URL_TEMPLATE.format(self._host, self._port, URL_CONTROL_NRC_DDD)

        res = urlopen(url, timeout=5).read()
        device_info = xmltodict.parse(res)["root"]["device"]

        return device_info

    def open_webpage(self, url):
        """Launch Web Browser and open url."""
        resource_id = 1063
        params = (
            "<X_AppType>vc_app</X_AppType>"
            f"<X_LaunchKeyword>resource_id={resource_id}</X_LaunchKeyword>"
        )
        res = self.soap_request(
            URL_CONTROL_NRC, URN_REMOTE_CONTROL, "X_LaunchApp", params, body_elem="s"
        )
        root = ElementTree.fromstring(res)
        el_session_id = root.find(".//X_SessionId")

        # setup a server socket where URL will be served
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        localip = self._get_local_ip()
        localport = random.randint(1025, 65535)
        server_socket.bind((localip, localport))
        server_socket.listen(1)
        _LOGGER.debug("Listening on %s:%d", localip, localport)

        params = (
            "<X_AppType>vc_app</X_AppType>"
            f"<X_SessionId>{el_session_id.text}</X_SessionId>"
            "<X_ConnectKeyword>panasonic-viera 0.2</X_ConnectKeyword>"
            f"<X_ConnectAddr>{localip}:{localport}</X_ConnectAddr>"
        )

        self.soap_request(
            URL_CONTROL_NRC, URN_REMOTE_CONTROL, "X_ConnectApp", params, body_elem="s"
        )

        sockfd, addr = server_socket.accept()
        _LOGGER.debug("Client (%s, %s) connected" % addr)
        packet = bytearray([0xF4, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, len(url)])
        packet.extend(map(ord, url))
        packet.append(0x00)
        sockfd.send(packet)
        sockfd.close()

        server_socket.close()

    def get_apps(self):
        """Return the list of apps on the TV."""
        res = self.soap_request(
            URL_CONTROL_NRC, URN_REMOTE_CONTROL, "X_GetAppList", None
        )

        apps = res.split("vc_app")[1:]
        app_list = {}
        for app in apps:
            prod_id = re.search("(?<=product_id\=)(.*?)(?=&apos;)", app).group(0)
            name = re.search("(?<=" + prod_id + "&apos;)(.*?)(?=&apos;)", app).group(0)
            app_list[name] = prod_id
        return app_list

    def get_vector_info(self):
        """Return the vector info on the TV."""
        res = self.soap_request(
            URL_CONTROL_NRC, URN_REMOTE_CONTROL, "X_GetVectorInfo", None
        )

        return res

    def get_volume(self):
        """Return the current volume level."""
        params = "<InstanceID>0</InstanceID><Channel>Master</Channel>"
        res = self.soap_request(
            URL_CONTROL_DMR, URN_RENDERING_CONTROL, "GetVolume", params
        )
        root = ElementTree.fromstring(res)
        el_volume = root.find(".//CurrentVolume")
        return int(el_volume.text)

    def set_volume(self, volume):
        """Set a new volume level."""
        if volume > 100 or volume < 0:
            raise Exception(
                "Bad request to volume control. " "Must be between 0 and 100"
            )
        params = (
            "<InstanceID>0</InstanceID><Channel>Master</Channel>"
            f"<DesiredVolume>{volume}</DesiredVolume>"
        )
        self.soap_request(URL_CONTROL_DMR, URN_RENDERING_CONTROL, "SetVolume", params)

    def get_mute(self):
        """Return if the TV is muted."""
        params = "<InstanceID>0</InstanceID><Channel>Master</Channel>"
        res = self.soap_request(
            URL_CONTROL_DMR, URN_RENDERING_CONTROL, "GetMute", params
        )
        root = ElementTree.fromstring(res)
        el_mute = root.find(".//CurrentMute")
        return el_mute.text != "0"

    def set_mute(self, enable):
        """Mute or unmute the TV."""
        data = "1" if enable else "0"
        params = (
            "<InstanceID>0</InstanceID><Channel>Master</Channel>"
            f"<DesiredMute>{data}</DesiredMute>"
        )
        self.soap_request(URL_CONTROL_DMR, URN_RENDERING_CONTROL, "SetMute", params)

    def send_key(self, key):
        """Send a key command to the TV."""
        if isinstance(key, Keys):
            key = key.value
        params = f"<X_KeyEvent>{key}</X_KeyEvent>"
        self.soap_request(URL_CONTROL_NRC, URN_REMOTE_CONTROL, "X_SendKey", params)

    def launch_app(self, app):
        """Launch an app."""
        if isinstance(app, Apps):
            app = app.value
        params = "<X_AppType>vc_app</X_AppType><X_LaunchKeyword>"
        if len(app) != 16:
            params = params + f"resource_id={app}</X_LaunchKeyword>"
        else:
            params = params + f"product_id={app}</X_LaunchKeyword>"
        self.soap_request(URL_CONTROL_NRC, URN_REMOTE_CONTROL, "X_LaunchApp", params)

    def turn_off(self):
        """Turn off media player."""
        self.send_key(Keys.POWER)

    def turn_on(self):
        """Turn on media player."""
        self.send_key(Keys.POWER)

    def volume_up(self):
        """Volume up the media player."""
        self.send_key(Keys.VOLUME_UP)

    def volume_down(self):
        """Volume down media player."""
        self.send_key(Keys.VOLUME_DOWN)

    def mute_volume(self):
        """Send mute command."""
        self.send_key(Keys.MUTE)

    def media_play(self):
        """Send play command."""
        self.send_key(Keys.PLAY)

    def media_pause(self):
        """Send media pause command to media player."""
        self.send_key(Keys.PAUSE)

    def media_next_track(self):
        """Send next track command."""
        self.send_key(Keys.FAST_FORWARD)

    def media_previous_track(self):
        """Send the previous track command."""
        self.send_key(Keys.REWIND)

    @property
    def type(self):
        """Return TV type."""
        return self._type

    @property
    def app_id(self):
        """Return application ID."""
        return self._app_id

    @property
    def enc_key(self):
        """Return encryption key."""
        return self._enc_key
