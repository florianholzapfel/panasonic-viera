"""Module to interact with your Panasonic Viera TV."""
from enum import Enum
import logging
import socket
import xml.etree.ElementTree as ET
from urllib.request import urlopen, Request

_LOGGER = logging.getLogger(__name__)

URN_RENDERING_CONTROL = 'schemas-upnp-org:service:RenderingControl:1'
URN_REMOTE_CONTROL = 'panasonic-com:service:p00NetworkControl:1'

URL_CONTROL_DMR = 'dmr/control_0'
URL_CONTROL_NRC = 'nrc/control_0'

DEFAULT_PORT = 55000

class Keys(Enum):
    """Contains all known keys."""
    thirty_second_skip = 'NRC_30S_SKIP-ONOFF'
    toggle_3d = 'NRC_3D-ONOFF'
    apps = 'NRC_APPS-ONOFF'
    aspect = 'NRC_ASPECT-ONOFF'
    blue = 'NRC_BLUE-ONOFF'
    cancel = 'NRC_CANCEL-ONOFF'
    cc = 'NRC_CC-ONOFF'
    chat_mode = 'NRC_CHAT_MODE-ONOFF'
    ch_down = 'NRC_CH_DOWN-ONOFF'
    input_key = 'NRC_CHG_INPUT-ONOFF'
    network = 'NRC_CHG_NETWORK-ONOFF'
    ch_up = 'NRC_CH_UP-ONOFF'
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

class RemoteControl:
    """This class represents a Panasonic Viera TV Remote Control."""

    def __init__(self, host, port=DEFAULT_PORT):
        """Initialise the remote control."""
        self._host = host
        self._port = port

    def soap_request(self, url, urn, action, params):
        """Send a SOAP request to the TV."""
        soap_body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"'
            ' s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            '<s:Body>'
            '<m:{action} xmlns:m="urn:{urn}">'
            '{params}'
            '</m:{action}>'
            '</s:Body>'
            '</s:Envelope>'
        ).format(action=action, urn=urn, params=params).encode('utf-8')

        headers = {
            'Host': '{}:{}'.format(self._host, self._port),
            'Content-Length': len(soap_body),
            'Content-Type': 'text/xml; charset=utf-8"',
            'SOAPAction': '"urn:{}#{}"'.format(urn, action),
        }

        url = 'http://{}:{}/{}'.format(self._host, self._port, url)

        _LOGGER.debug("Sending to %s:\n%s\n%s", url, headers, soap_body)
        req = Request(url, soap_body, headers)

        res = urlopen(req, timeout=2).read()
        _LOGGER.debug("Response: %s", res)
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
        params = '<X_KeyEvent>{}</X_KeyEvent>'.format(key)
        self.soap_request(URL_CONTROL_NRC, URN_REMOTE_CONTROL,
                          'X_SendKey', params)

    def turn_off(self):
        """Turn off media player."""
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
