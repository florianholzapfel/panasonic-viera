"""Tests for the open_webpage packet format."""

import unittest

from panasonic_viera import RemoteControl


class WebpagePacketTests(unittest.TestCase):
    def test_short_url_matches_legacy_format(self):
        url = "http://example.com/"
        legacy = bytearray([0xF4, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, len(url)])
        legacy.extend(map(ord, url))
        legacy.append(0x00)
        self.assertEqual(RemoteControl._build_webpage_packet(url), bytes(legacy))

    def test_url_longer_than_255_bytes(self):
        url = "http://example.com/" + "a" * (300 - len("http://example.com/"))
        packet = RemoteControl._build_webpage_packet(url)
        self.assertEqual(packet[:4], b"\xf4\x01\x01\x00")
        self.assertEqual(packet[4:8], b"\x00\x00\x01\x2c")
        self.assertEqual(packet[8:-1], url.encode("ascii"))
        self.assertEqual(packet[-1:], b"\x00")

    def test_non_ascii_url_is_utf8_encoded(self):
        url = "http://example.com/ü€"
        packet = RemoteControl._build_webpage_packet(url)
        encoded = url.encode("utf-8")
        self.assertEqual(packet[4:8], len(encoded).to_bytes(4, "big"))
        self.assertEqual(packet[8:-1], encoded)


if __name__ == "__main__":
    unittest.main()
