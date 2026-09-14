"""Regression tests for SOAP session sequence handling."""

import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from panasonic_viera import RemoteControl, URL_CONTROL_NRC, URN_REMOTE_CONTROL


class SoapSequenceTests(unittest.TestCase):
    def setUp(self):
        self.remote = RemoteControl.__new__(RemoteControl)
        self.remote._host = "tv.invalid"
        self.remote._port = 55000
        self.remote._app_id = "test-app"
        self.remote._session_key = b"0" * 16
        self.remote._session_iv = b"0" * 16
        self.remote._session_hmac_key = b"0" * 32
        self.remote._session_id = "test-session"
        self.remote._session_seq_num = 42
        self.remote._encrypt_soap_payload = Mock(return_value="encrypted")
        self.remote._decrypt_soap_payload = Mock(return_value="ok")

    def test_pac_errors_preserve_sequence_for_next_encrypted_command(self):
        for operation in (self.remote.list_inputs, self.remote.set_picture_mode):
            with self.subTest(operation=operation.__name__):
                self.remote._session_seq_num = 42
                error = HTTPError("http://tv.invalid", 404, "Not Found", {}, None)
                with patch("panasonic_viera.remote_control.urlopen", side_effect=error):
                    with self.assertRaises(HTTPError) as raised:
                        if operation == self.remote.set_picture_mode:
                            operation("Cinema")
                        else:
                            operation()
                self.assertIs(raised.exception, error)
                self.assertEqual(self.remote._session_seq_num, 42)

                response = Mock()
                response.read.return_value = b"<root><X_EncResult>data</X_EncResult></root>"
                with patch("panasonic_viera.remote_control.urlopen", return_value=response):
                    self.remote.soap_request(
                        URL_CONTROL_NRC, URN_REMOTE_CONTROL, "X_SendKey", ""
                    )
                payload = self.remote._encrypt_soap_payload.call_args.args[0]
                self.assertIn("<X_SequenceNumber>00000043</X_SequenceNumber>", payload)
                self.assertEqual(self.remote._session_seq_num, 43)

    def test_encrypted_http_error_rolls_back_sequence(self):
        error = HTTPError("http://tv.invalid", 500, "Server Error", {}, None)
        with patch("panasonic_viera.remote_control.urlopen", side_effect=error):
            with self.assertRaises(HTTPError) as raised:
                self.remote.soap_request(
                    URL_CONTROL_NRC, URN_REMOTE_CONTROL, "X_SendKey", ""
                )
        self.assertIs(raised.exception, error)
        payload = self.remote._encrypt_soap_payload.call_args.args[0]
        self.assertIn("<X_SequenceNumber>00000043</X_SequenceNumber>", payload)
        self.assertEqual(self.remote._session_seq_num, 42)
