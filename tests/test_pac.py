"""Tests for the narrow Panasonic PAC controls."""

import unittest
from unittest.mock import Mock, patch

from panasonic_viera import RemoteControl, SOAPError


class PacControlTests(unittest.TestCase):
    def setUp(self):
        self.remote = RemoteControl.__new__(RemoteControl)

    def test_lists_and_reads_inputs(self):
        self.remote._pac_inquiry = Mock(
            side_effect=["QIL:TV[TV],H1[HDMI1],H2[HDMI2]", "QMI:H2", "QIL:TV[TV],H1[HDMI1],H2[HDMI2]"]
        )
        self.assertEqual(self.remote.list_inputs(), ["TV", "HDMI1", "HDMI2"])
        self.assertEqual(self.remote.get_input(), "HDMI2")

    def test_sets_input_and_waits_for_readback(self):
        self.remote._pac_inquiry = Mock(
            side_effect=["QIL:H1[HDMI1],H2[HDMI2]", "QMI:H1", "QIL:H1[HDMI1],H2[HDMI2]", "QMI:H2", "QIL:H1[HDMI1],H2[HDMI2]"]
        )
        self.remote._pac_control = Mock()
        with patch("panasonic_viera.remote_control.time.sleep"):
            self.assertEqual(self.remote.set_input("HDMI2"), "HDMI2")
        self.remote._pac_control.assert_called_once_with("IMS:H2")

    def test_rejects_unknown_input(self):
        self.remote._pac_inquiry = Mock(return_value="QIL:H1[HDMI1]")
        with self.assertRaises(ValueError):
            self.remote.set_input("HDMI9")

    def test_picture_modes_and_readback(self):
        self.assertIn("Game", self.remote.list_picture_modes())
        self.remote._pac_inquiry = Mock(side_effect=["QPC:STD", "QPC:CNM"])
        self.remote._pac_control = Mock()
        with patch("panasonic_viera.remote_control.time.sleep"):
            self.assertEqual(self.remote.set_picture_mode("Cinema"), "Cinema")
        self.remote._pac_control.assert_called_once_with("VPC:CNM")

    def test_rejects_unexpected_pac_value(self):
        with self.assertRaises(SOAPError):
            self.remote._pac_value("QPW:1", "QMI")

    def test_extracts_pac_result_without_expanding_entities(self):
        response = """\
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
          <s:Body>
            <u:X_SendInquiryCmdResponse xmlns:u="urn:panasonic-com:service:p00NetworkControl:1">
              <X_InquiryCmdResult>QMI:H1</X_InquiryCmdResult>
            </u:X_SendInquiryCmdResponse>
          </s:Body>
        </s:Envelope>
        """

        self.assertEqual(self.remote._pac_result(response, "X_InquiryCmdResult"), "QMI:H1")


if __name__ == "__main__":
    unittest.main()
