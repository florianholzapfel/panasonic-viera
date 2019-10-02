"""Module to interact with your Panasonic Viera TV."""
from enum import Enum
import logging
import random
import socket
import xml.etree.ElementTree as ET
import base64
import binascii
import struct
import hmac, hashlib
import time
from Crypto.Cipher import AES
try:
    from urllib.request import urlopen, Request, HTTPError
except:
    from urllib2 import urlopen, Request, HTTPError

_LOGGER = logging.getLogger(__name__)

URN_RENDERING_CONTROL = 'schemas-upnp-org:service:RenderingControl:1'
URN_REMOTE_CONTROL = 'panasonic-com:service:p00NetworkControl:1'

URL_CONTROL_NRC_DEF = 'nrc/sdd_0.xml'
URL_CONTROL_DMR = 'dmr/control_0'
URL_CONTROL_NRC = 'nrc/control_0'

TV_TYPE_NONENCRYPTED = 0
TV_TYPE_ENCRYPTED = 1

DEFAULT_PORT = 55000

BLOCK_SIZE = 16  # Bytes
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(0)

class Keys(Enum):
    """Contains all known keys."""
    thirty_second_skip = 'NRC_30S_SKIP-ONOFF'
    toggle_3d = 'NRC_3D-ONOFF'
    apps = 'NRC_APPS-ONOFF'
    aspect = 'NRC_ASPECT-ONOFF'
    back = 'NRC_RETURN-ONOFF'
    blue = 'NRC_BLUE-ONOFF'
    cancel = 'NRC_CANCEL-ONOFF'
    cc = 'NRC_CC-ONOFF'
    chat_mode = 'NRC_CHAT_MODE-ONOFF'
    ch_down = 'NRC_CH_DOWN-ONOFF'
    input_key = 'NRC_CHG_INPUT-ONOFF'
    network = 'NRC_CHG_NETWORK-ONOFF'
    ch_up = 'NRC_CH_UP-ONOFF'
    num_0 = 'NRC_D0-ONOFF'
    num_1 = 'NRC_D1-ONOFF'
    num_2 = 'NRC_D2-ONOFF'
    num_3 = 'NRC_D3-ONOFF'
    num_4 = 'NRC_D4-ONOFF'
    num_5 = 'NRC_D5-ONOFF'
    num_6 = 'NRC_D6-ONOFF'
    num_7 = 'NRC_D7-ONOFF'
    num_8 = 'NRC_D8-ONOFF'
    num_9 = 'NRC_D9-ONOFF'
    diga_control = 'NRC_DIGA_CTL-ONOFF'
    display = 'NRC_DISP_MODE-ONOFF'
    down = 'NRC_DOWN-ONOFF'
    enter = 'NRC_ENTER-ONOFF'
    epg = 'NRC_EPG-ONOFF'
    exit = 'NRC_CANCEL-ONOFF'
    ez_sync = 'NRC_EZ_SYNC-ONOFF'
    favorite = 'NRC_FAVORITE-ONOFF'
    fast_forward = 'NRC_FF-ONOFF'
    game = 'NRC_GAME-ONOFF'
    green = 'NRC_GREEN-ONOFF'
    guide = 'NRC_GUIDE-ONOFF'
    hold = 'NRC_HOLD-ONOFF'
    home = 'NRC_HOME-ONOFF'
    index = 'NRC_INDEX-ONOFF'
    info = 'NRC_INFO-ONOFF'
    connect = 'NRC_INTERNET-ONOFF'
    left = 'NRC_LEFT-ONOFF'
    menu = 'NRC_MENU-ONOFF'
    mpx = 'NRC_MPX-ONOFF'
    mute = 'NRC_MUTE-ONOFF'
    net_bs = 'NRC_NET_BS-ONOFF'
    net_cs = 'NRC_NET_CS-ONOFF'
    net_td = 'NRC_NET_TD-ONOFF'
    off_timer = 'NRC_OFFTIMER-ONOFF'
    pause = 'NRC_PAUSE-ONOFF'
    pictai = 'NRC_PICTAI-ONOFF'
    play = 'NRC_PLAY-ONOFF'
    p_nr = 'NRC_P_NR-ONOFF'
    power = 'NRC_POWER-ONOFF'
    program = 'NRC_PROG-ONOFF'
    record = 'NRC_REC-ONOFF'
    red = 'NRC_RED-ONOFF'
    return_key = 'NRC_RETURN-ONOFF'
    rewind = 'NRC_REW-ONOFF'
    right = 'NRC_RIGHT-ONOFF'
    r_screen = 'NRC_R_SCREEN-ONOFF'
    last_view = 'NRC_R_TUNE-ONOFF'
    sap = 'NRC_SAP-ONOFF'
    toggle_sd_card = 'NRC_SD_CARD-ONOFF'
    skip_next = 'NRC_SKIP_NEXT-ONOFF'
    skip_prev = 'NRC_SKIP_PREV-ONOFF'
    split = 'NRC_SPLIT-ONOFF'
    stop = 'NRC_STOP-ONOFF'
    subtitles = 'NRC_STTL-ONOFF'
    option = 'NRC_SUBMENU-ONOFF'
    surround = 'NRC_SURROUND-ONOFF'
    swap = 'NRC_SWAP-ONOFF'
    text = 'NRC_TEXT-ONOFF'
    tv = 'NRC_TV-ONOFF'
    up = 'NRC_UP-ONOFF'
    link = 'NRC_VIERA_LINK-ONOFF'
    volume_down = 'NRC_VOLDOWN-ONOFF'
    volume_up = 'NRC_VOLUP-ONOFF'
    vtools = 'NRC_VTOOLS-ONOFF'
    yellow = 'NRC_YELLOW-ONOFF'

class Apps(Enum):
    """Contains several app product IDs."""
    netflix = '0010000200000001'
    youtube = '0070000200180001'
    shoutcast = '0070000400000001'
    calendar = '0387878700150020'
    #browser = '1063'
    browser = '0077777700160002'
    amazonprime = '0010000100180001'
    iplayer = '0020000A00000010'
    bbciplayer = '0020000A00000010'
    itv = '0387878700000124'
    all4 = '0387878700000125'
    demand5 = '0020009300000001'
    recordedtv = '0387878700000013'
    multiwindow = '0387878700000050'
    bbcnews = '0020000A00000006'
    bbcsport = '0020000A00000007'
    weather = '0070000C00000001'
    developer = '0077777777777778'
    
class SOAPError(Exception):
    pass

class EncryptionRequired(Exception):
    pass

class RemoteControl:
    """This class represents a Panasonic Viera TV Remote Control."""

    def __init__(self, host, port=DEFAULT_PORT, app_id=None, encryption_key=None):
        """Initialise the remote control."""
        self._host = host
        self._port = port
        self._app_id = app_id
        self._enc_key = encryption_key
        self._session_key = None
        self._session_iv = None
        self._session_id = None
        self._session_seq_num = None
        self._session_hmac_key = None
        
        if self._app_id is None or self._enc_key is None:
            self._type = TV_TYPE_NONENCRYPTED
        else:
            self._type = TV_TYPE_ENCRYPTED
            self._derive_session_keys()
            self._request_session_id()
        
        # Determine if the TV uses encryption or not
        if self._type == TV_TYPE_NONENCRYPTED:
            url = 'http://{}:{}/{}'.format(self._host, self._port,  URL_CONTROL_NRC_DEF)
            
            _LOGGER.debug("Determining TV type\n")
            res = urlopen(url, timeout=5).read()
            root = ET.fromstring(res)
            for child in root:
                if child.tag.endswith("actionList"):
                    for subchild in child.iter():
                        if subchild.tag.endswith("name"):
                            if subchild.text == "X_GetEncryptSessionId":
                                self._type = TV_TYPE_ENCRYPTED
            _LOGGER.debug("Determined TV type is %s\n", "encrypted" if self._type == TV_TYPE_ENCRYPTED else "non-encrypted")

    def soap_request(self, url, urn, action, params, body_elem="m"):
        """Send a SOAP request to the TV."""
        
        is_encrypted = False
        
        # Encapsulate URN_REMOTE_CONTROL command in an X_EncryptedCommand if we're using encryption
        if urn == URN_REMOTE_CONTROL and action not in ["X_GetEncryptSessionId", "X_DisplayPinCode", "X_RequestAuth"]:
            if None not in [self._session_key, self._session_iv, self._session_hmac_key, self._session_id, self._session_seq_num]:
                is_encrypted = True
                self._session_seq_num += 1
                encrypted_command = (
                    '<X_SessionId>{session_id}</X_SessionId>'
                    '<X_SequenceNumber>{seq_num}</X_SequenceNumber>'
                    '<X_OriginalCommand>'
                    '<{body_elem}:{action} xmlns:{body_elem}="urn:{urn}">'
                    '{params}'
                    '</{body_elem}:{action}>'
                    '</X_OriginalCommand>'
                ).format(session_id=self._session_id, seq_num='%08d' % self._session_seq_num, action=action, urn=urn, 
                    params=params, body_elem="u").encode('utf-8')
                
                encrypted_command = self._encrypt_soap_payload(encrypted_command, self._session_key, self._session_iv,
                    self._session_hmac_key)
                
                action = 'X_EncryptedCommand'
                params = ('<X_ApplicationId>{application_id}</X_ApplicationId>'
                            '<X_EncInfo>{encrypted_command}</X_EncInfo>'
                            ).format(application_id=self._app_id, encrypted_command=encrypted_command)
                body_elem = "u"
            elif self._type == TV_TYPE_ENCRYPTED:
                raise EncryptionRequired("Please refer to the docs for using encryption")
        
        # Construct SOAP request
        soap_body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"'
            ' s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            '<s:Body>'
            '<{body_elem}:{action} xmlns:{body_elem}="urn:{urn}">'
            '{params}'
            '</{body_elem}:{action}>'
            '</s:Body>'
            '</s:Envelope>'
        ).format(action=action, urn=urn, params=params, body_elem=body_elem).encode('utf-8')

        headers = {
            'Host': '{}:{}'.format(self._host, self._port),
            'Content-Length': len(soap_body),
            'Content-Type': 'text/xml; charset=utf-8"',
            'SOAPAction': '"urn:{}#{}"'.format(urn, action),
        }

        url = 'http://{}:{}/{}'.format(self._host, self._port, url)

        _LOGGER.debug("Sending to %s:\n%s\n%s", url, headers, soap_body)
        req = Request(url, soap_body, headers)
        try:
            res = urlopen(req, timeout=5).read()
        except HTTPError, e:
            if self._session_seq_num is not None:
                self._session_seq_num -= 1
            raise Exception(e) # Pass to the next handler
        _LOGGER.debug("Response: %s", res)
        
        if is_encrypted:
            root = ET.fromstring(res)
            enc_result = root.find('.//X_EncResult').text
            enc_result_decrypted = self._decrypt_soap_payload(
                    enc_result, self._session_key, self._session_iv, self._session_hmac_key
            ) 
            res = enc_result_decrypted
        
        return res
    
    def _derive_session_keys(self):
        iv = base64.b64decode(self._enc_key)
        
        self._session_iv = iv
        
        # Get character codes from IV bytes
        iv_vals = [ord(c) for c in iv]
        
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
        self._session_key = ''.join(chr(c) for c in key_vals)
        
        # HMAC key for comms is just the IV repeated twice
        self._session_hmac_key = iv * 2
    
    def _encrypt_soap_payload(self, data, key, iv, hmac_key):
        # The encrypted payload must begin with a 16-byte header (12 random bytes, and 4 bytes for the payload length in big endian)
        # Note: the server does not appear to ever send back valid payload lengths in bytes 13-16, so I would assume these can also 
        # be randomized by the client, but we'll set them anyway to be safe.
        payload = ''.join(chr(random.randint(0,255)) for i in range(12))
        payload += struct.pack(">I", len(data))
        payload += data
        
        # Initialize AES-CBC with key and IV
        aes = AES.new(key, AES.MODE_CBC, iv)
        # Encrypt with zero-padding
        ciphertext = aes.encrypt(pad(payload))
        # Compute HMAC-SHA-256
        sig = hmac.new(hmac_key, ciphertext, hashlib.sha256).digest()
        # Concat HMAC with AES-encrypted payload
        return base64.b64encode(ciphertext + sig)
    
    def _decrypt_soap_payload(self, data, key, iv, hmac_key):
        # Initialize AES-CBC with key and IV
        aes = AES.new(key, AES.MODE_CBC, iv)
        # Decrypt
        decrypted = aes.decrypt(base64.b64decode(data))
        # Unpad and return
        return decrypted[16:].split("\0")[0]
    
    def request_pin_code(self, name='My Remote'):
        # First let's ask for a pin code and get a challenge key back
        params = '<X_DeviceName>' + name + '</X_DeviceName>'
        try:
            res = self.soap_request(URL_CONTROL_NRC, URN_REMOTE_CONTROL, 'X_DisplayPinCode', params, body_elem="u")
        except HTTPError, e:
            if e.code == 500:
                xml = ET.fromstring(e.fp.read())
                for child in xml.iter():
                    if child.tag.endswith("errorDescription"):
                        raise SOAPError(child.text)
                return
        root = ET.fromstring(res)
        self._challenge = base64.b64decode(root.find('.//X_ChallengeKey').text)
    
    def authorize_pin_code(self, pincode):
        # Second, let's encrypt the pin code using the challenge key and send it back to authenticate
        
        # Derive key from IV
        iv = self._challenge
        key = ""
        i = 0
        while i < 16:
            key += chr(~ord(iv[i + 3]) & 0xFF)
            key += chr(~ord(iv[i + 2]) & 0xFF)
            key += chr(~ord(iv[i + 1]) & 0xFF)
            key += chr(~ord(iv[i]) & 0xFF)
            i += 4
        
        # Derive HMAC key from IV & HMAC key mask (taken from libtvconnect.so)
        hmac_key_mask_vals = [0x15,0xC9,0x5A,0xC2,0xB0,0x8A,0xA7,0xEB,0x4E,0x22,0x8F,0x81,0x1E,0x34,0xD0,0x4F,0xA5,0x4B,0xA7,0xDC,0xAC,0x98,0x79,0xFA,0x8A,0xCD,0xA3,0xFC,0x24,0x4F,0x38,0x54]
        hmac_key = ""
        i = 0
        while i < 32:
            hmac_key += chr(hmac_key_mask_vals[i] ^ ord(iv[(i + 2) & 0xF]))
            hmac_key += chr(hmac_key_mask_vals[i + 1] ^ ord(iv[(i + 3) & 0xF]))
            hmac_key += chr(hmac_key_mask_vals[i + 2] ^ ord(iv[i & 0xF]))
            hmac_key += chr(hmac_key_mask_vals[i + 3] ^ ord(iv[(i + 1) & 0xF]))
            i += 4
        
        # Encrypt X_PinCode argument and send it within an X_AuthInfo tag
        params = '<X_AuthInfo>' + self._encrypt_soap_payload("<X_PinCode>" + pincode + "</X_PinCode>", key, iv, hmac_key) + '</X_AuthInfo>'
        try:
            res = self.soap_request(URL_CONTROL_NRC, URN_REMOTE_CONTROL, 'X_RequestAuth', params, body_elem="u")
        except HTTPError, e:
            if e.code == 500:
                xml = ET.fromstring(e.fp.read())
                for child in xml.iter():
                    if child.tag.endswith("errorCode") and child.text == "600":
                        raise SOAPError("Invalid PIN Code!")
                    elif child.tag.endswith("errorDescription"):
                        raise SOAPError(child.text)
                return
        
        # Parse and decrypt X_AuthResult
        root = ET.fromstring(res)
        auth_result = root.find('.//X_AuthResult').text
        auth_result_decrypted = ET.fromstring("<X_Data>" + self._decrypt_soap_payload(auth_result, key, iv, hmac_key) + "</X_Data>")
        
        # Set session application ID and encryption key
        self._app_id = auth_result_decrypted.find(".//X_ApplicationId").text
        self._enc_key = auth_result_decrypted.find(".//X_Keyword").text
        
        # Derive AES & HMAC keys from X_Keyword
        self._derive_session_keys()
        
        # Request a session
        self._request_session_id()
    
    def _request_session_id(self):
        # Thirdly, let's ask for a session. We'll need to use a valid session ID for encrypted NRC commands.
        
        # We need to send an encrypted version of X_ApplicationId
        encinfo = self._encrypt_soap_payload(
                '<X_ApplicationId>' + self._app_id + '</X_ApplicationId>',
                self._session_key,
                self._session_iv,
                self._session_hmac_key)

        # Send the encrypted SOAP request along with plaintext X_ApplicationId
        params = ('<X_ApplicationId>{application_id}</X_ApplicationId>'
                 '<X_EncInfo>{enc_info}</X_EncInfo>'
                 ).format(application_id=self._app_id, enc_info=encinfo)
        try:
            res = self.soap_request(URL_CONTROL_NRC, URN_REMOTE_CONTROL,
                                    'X_GetEncryptSessionId', params, body_elem="u")
        except HTTPError, e:
            if e.code == 500:
                xml = ET.fromstring(e.fp.read())
                for child in xml.iter():
                    if child.tag.endswith("errorDescription"):
                        raise SOAPError(child.text)
                return
        
        root = ET.fromstring(res)
        enc_result = root.find('.//X_EncResult').text
        enc_result_decrypted = ET.fromstring(
                "<X_Data>" + 
                self._decrypt_soap_payload(
                        enc_result, self._session_key, self._session_iv, self._session_hmac_key
                        ) 
                + "</X_Data>"
                )
        
        # Set session ID and begin sequence number at 1. We have to increment the sequence number upon each successful NRC command.
        self._session_id = enc_result_decrypted.find('.//X_SessionId').text
        self._session_seq_num = 1

    # Taken from https://github.com/home-assistant/ file: home-assistant/homeassistant/util/__init__.py
    def _get_local_ip(self):
        """Try to determine the local IP address of the machine."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Use Google Public DNS server to determine own IP
            sock.connect(('8.8.8.8', 80))

            return sock.getsockname()[0]
        except socket.error:
            try:
                return socket.gethostbyname(socket.gethostname())
            except socket.gaierror:
                return '127.0.0.1'
        finally:
            sock.close()

    def open_webpage(self, url):
        """Launch Web Browser and open url"""
        params = ('<X_AppType>vc_app</X_AppType>'
                 '<X_LaunchKeyword>resource_id={resource_id}</X_LaunchKeyword>'
                 ).format(resource_id=1063)
        res = self.soap_request(URL_CONTROL_NRC, URN_REMOTE_CONTROL,
                                'X_LaunchApp', params, body_elem="s")
        root = ET.fromstring(res)
        el_sessionId = root.find('.//X_SessionId')

        #setup a server socket where URL will be served
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        localip = self._get_local_ip() 
        localport = random.randint(1025,65535)
        server_socket.bind((localip, localport))
        server_socket.listen(1)
        _LOGGER.debug("Listening on {}:{}".format(localip,localport))
 
        params = ('<X_AppType>vc_app</X_AppType>'
                 '<X_SessionId>{sessionId}</X_SessionId>'
                 '<X_ConnectKeyword>panasonic-viera 0.2</X_ConnectKeyword>'
                 '<X_ConnectAddr>{localip}:{localport}</X_ConnectAddr>'
                 ).format(sessionId=el_sessionId.text, localip=localip, localport=localport)

        res = self.soap_request(URL_CONTROL_NRC, URN_REMOTE_CONTROL,
                                'X_ConnectApp', params, body_elem="s")

        sockfd, addr = server_socket.accept()
        _LOGGER.debug("Client (%s, %s) connected" % addr)
        packet = bytearray([0xf4, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, len(url)])
        packet.extend(map(ord, url))
        packet.append(0x00)
        sockfd.send(packet)
        sockfd.close()

        server_socket.close()
    
    def get_apps(self):
        """Return the list of apps on the TV"""
        res = self.soap_request(URL_CONTROL_NRC, URN_REMOTE_CONTROL,
                                'X_GetAppList', None)
        
        return res
    
    def get_vector_info(self):
        """Return the vector info on the TV"""
        res = self.soap_request(URL_CONTROL_NRC, URN_REMOTE_CONTROL,
                                'X_GetVectorInfo', None)
        
        return res

    def get_volume(self):
        """Return the current volume level."""
        params = '<InstanceID>0</InstanceID><Channel>Master</Channel>'
        res = self.soap_request(URL_CONTROL_DMR, URN_RENDERING_CONTROL,
                                'GetVolume', params)
        root = ET.fromstring(res)
        el_volume = root.find('.//CurrentVolume')
        return int(el_volume.text)

    def set_volume(self, volume):
        """Set a new volume level."""
        if volume > 100 or volume < 0:
            raise Exception('Bad request to volume control. '
                            'Must be between 0 and 100')
        params = ('<InstanceID>0</InstanceID><Channel>Master</Channel>'
                  '<DesiredVolume>{}</DesiredVolume>').format(volume)
        self.soap_request(URL_CONTROL_DMR, URN_RENDERING_CONTROL,
                          'SetVolume', params)

    def get_mute(self):
        """Return if the TV is muted."""
        params = '<InstanceID>0</InstanceID><Channel>Master</Channel>'
        res = self.soap_request(URL_CONTROL_DMR, URN_RENDERING_CONTROL,
                                'GetMute', params)
        root = ET.fromstring(res)
        el_mute = root.find('.//CurrentMute')
        return el_mute.text != '0'

    def set_mute(self, enable):
        """Mute or unmute the TV."""
        data = '1' if enable else '0'
        params = ('<InstanceID>0</InstanceID><Channel>Master</Channel>'
                  '<DesiredMute>{}</DesiredMute>').format(data)
        self.soap_request(URL_CONTROL_DMR, URN_RENDERING_CONTROL,
                          'SetMute', params)

    def send_key(self, key):
        """Send a key command to the TV."""
        if isinstance(key, Keys):
            key = key.value
        params = '<X_KeyEvent>{}</X_KeyEvent>'.format(key)
        self.soap_request(URL_CONTROL_NRC, URN_REMOTE_CONTROL,
                          'X_SendKey', params)
    
    def launch_app(self, app):
        """Launch an app."""
        if isinstance(app, Apps):
            app = app.value
        params = '<X_AppType>vc_app</X_AppType><X_LaunchKeyword>'
        if len(app) != 16:
            params = params + 'resource_id={}</X_LaunchKeyword>'.format(app)
        else:
            params = params + 'product_id={}</X_LaunchKeyword>'.format(app)
        self.soap_request(URL_CONTROL_NRC, URN_REMOTE_CONTROL,
                          'X_LaunchApp', params)

    def turn_off(self):
        """Turn off media player."""
        self.send_key(Keys.power)

    def turn_on(self):
        """Turn on media player."""
        self.send_key(Keys.power)

    def volume_up(self):
        """Volume up the media player."""
        self.send_key(Keys.volume_up)

    def volume_down(self):
        """Volume down media player."""
        self.send_key(Keys.volume_down)

    def mute_volume(self):
        """Send mute command."""
        self.send_key(Keys.mute)

    def media_play(self):
        """Send play command."""
        self.send_key(Keys.play)

    def media_pause(self):
        """Send media pause command to media player."""
        self.send_key(Keys.pause)

    def media_next_track(self):
        """Send next track command."""
        self.send_key(Keys.fast_forward)

    def media_previous_track(self):
        """Send the previous track command."""
        self.send_key(Keys.rewind)
