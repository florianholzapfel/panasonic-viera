"""Module constants and utility functions for Panasonic Viera TV control."""

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
    """Pad string to block size with null characters."""
    return s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(0)