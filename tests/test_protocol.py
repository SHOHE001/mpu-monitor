import json
import unittest

from protocol import parse_message, stream_status


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

    def test_stale_and_sensor_error_override_old_valid_sample(self):
        self.assertEqual(stream_status(None, 2), "waiting")
        self.assertEqual(stream_status(1, 1.5), "live")
        self.assertEqual(stream_status(1, 2.1), "stale")
        self.assertEqual(stream_status(1, 1.1, True), "sensor_error")


if __name__ == "__main__":
    unittest.main()
