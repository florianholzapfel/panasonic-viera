"""Module to interact with your Panasonic Viera TV."""
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
        self.send_key('NRC_POWER-ONOFF')

    def volume_up(self):
        """Volume up the media player."""
        self.send_key('NRC_VOLUP-ONOFF')

    def volume_down(self):
        """Volume down media player."""
        self.send_key('NRC_VOLDOWN-ONOFF')

    def mute_volume(self):
        """Send mute command."""
        self.send_key('NRC_MUTE-ONOFF')

    def media_play(self):
        """Send play command."""
        self.send_key('NRC_PLAY-ONOFF')

    def media_pause(self):
        """Send media pause command to media player."""
        self.send_key('NRC_PAUSE-ONOFF')

    def media_next_track(self):
        """Send next track command."""
        self.send_key('NRC_FF-ONOFF')

    def media_previous_track(self):
        """Send the previous track command."""
        self.send_key('NRC_REW-ONOFF')
