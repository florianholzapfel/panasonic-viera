"""Custom exceptions for Panasonic Viera TV control."""


class SOAPError(Exception):
    """This exception is thrown when a SOAP error happens."""


class EncryptionRequired(Exception):
    """This exception is thrown when encryption is required."""