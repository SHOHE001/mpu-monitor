import json
import unittest

from protocol import MAX_LINE_BYTES, MessageStream, parse_message, stream_status


class ProtocolTests(unittest.TestCase):
    def sample(self, **updates):
        obj = dict(v=1, type="sample", seq=1, ms=500, who=0x70, address=0x68,
                   accel=[0, 0, 1.0], gyro=[0, 0, 0], errors=0)
        obj.update(updates)
        return json.dumps(obj)

    def test_supported_ids(self):
        for who in (0x68, 0x70):
            self.assertIsNotNone(parse_message(self.sample(who=who)))

    def test_bad_packets_never_become_measurements(self):
        for packet in (b"ets Jul 29 2019", b"\xff\xfe", "[]", "{", self.sample(who=0x71),
                       self.sample(accel=[1, 2]), self.sample(gyro=[0, float('nan'), 0]),
                       self.sample(accel=[True, 0, 0]), self.sample(seq=-1), self.sample(errors="0")):
            with self.subTest(packet=packet):
                self.assertIsNone(parse_message(packet))

    def test_error_packet(self):
        packet = dict(v=1, type="error", code="i2c_read_failed", errors=3)
        self.assertEqual(parse_message(json.dumps(packet)), packet)

    def test_unrepresentable_numbers_are_ignored(self):
        for key in ("accel", "gyro"):
            for value in (10**400, -(10**400)):
                with self.subTest(key=key, negative=value < 0):
                    self.assertIsNone(parse_message(self.sample(**{key: [value, 0, 0]})))

    def test_nested_json_is_ignored(self):
        self.assertIsNone(parse_message(b"[" * 10000 + b"0" + b"]" * 10000))

    def test_version_must_be_integer_one(self):
        for version in (True, 1.0, "1", None):
            with self.subTest(version=version):
                self.assertIsNone(parse_message(self.sample(v=version)))
                self.assertIsNone(parse_message(json.dumps(
                    dict(v=version, type="error", code="i2c_read_failed", errors=1))))

    def test_stale_and_sensor_error_override_old_valid_sample(self):
        self.assertEqual(stream_status(None, 2), "waiting")
        self.assertEqual(stream_status(1, 1.5), "live")
        self.assertEqual(stream_status(1, 2.1), "stale")
        self.assertEqual(stream_status(1, 1.1, True), "sensor_error")


class MessageStreamTests(unittest.TestCase):
    def setUp(self):
        self.stream = MessageStream()
        self.packet = dict(v=1, type="error", code="i2c_read_failed", errors=3)
        self.line = json.dumps(self.packet).encode()

    def test_fragmented_packets_and_multiple_lines(self):
        self.assertEqual(self.stream.feed(self.line[:10]), [])
        self.assertEqual(self.stream.feed(self.line[10:] + b"\r\n" + self.line + b"\n"),
                         [self.packet, self.packet])

    def test_boot_chatter_and_malformed_line_do_not_hide_next_packet(self):
        chunk = b"ets Jul 29 2019\n\xff\xfe\n{\n" + self.line + b"\n"
        self.assertEqual(self.stream.feed(chunk), [self.packet])

    def test_exact_size_limit_is_accepted(self):
        padding = b" " * (MAX_LINE_BYTES - len(self.line))
        self.assertEqual(self.stream.feed(padding + self.line + b"\n"), [self.packet])

    def test_complete_oversized_line_is_rejected(self):
        padding = b" " * (MAX_LINE_BYTES - len(self.line) + 1)
        self.assertEqual(self.stream.feed(padding + self.line + b"\n" + self.line + b"\n"),
                         [self.packet])

    def test_oversized_line_suffix_is_discarded_through_newline(self):
        self.assertEqual(self.stream.feed(b"x" * MAX_LINE_BYTES), [])
        self.assertEqual(self.stream.feed(b"x"), [])
        self.assertEqual(self.stream.feed(self.line + b"\n"), [])
        self.assertEqual(self.stream.feed(self.line + b"\n"), [self.packet])

    def test_oversized_line_does_not_keep_growing(self):
        for _ in range(10):
            self.assertEqual(self.stream.feed(b"x" * MAX_LINE_BYTES), [])
            self.assertLessEqual(len(self.stream.buffer), MAX_LINE_BYTES)
        self.assertEqual(self.stream.feed(b"\n" + self.line + b"\n"), [self.packet])


if __name__ == "__main__":
    unittest.main()
