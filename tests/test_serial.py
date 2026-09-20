"""Exercise the reader with simulated serial devices; never open hardware."""
from collections import deque
import json
import queue
import unittest
from unittest.mock import patch

try:
    import serial
    from monitor import SerialReader
except ImportError:
    SerialReader = None


class FakeDevice:
    def __init__(self, reader, chunks, fail_at_end=False):
        self.reader = reader
        self.chunks = deque(chunks)
        self.fail_at_end = fail_at_end
        self.closed = False
        self.opened = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def open(self):
        self.opened = True

    @property
    def in_waiting(self):
        return len(self.chunks[0]) if self.chunks else 0

    def read(self, size):
        if not self.chunks:
            if self.fail_at_end:
                raise serial.SerialException("simulated disconnect")
            self.reader.stop_event.set()
            return b""
        chunk = self.chunks.popleft()
        if len(chunk) > size:
            self.chunks.appendleft(chunk[size:])
        return chunk[:size]


@unittest.skipIf(SerialReader is None, "Tkinter and pySerial required")
class SerialReaderTests(unittest.TestCase):
    def setUp(self):
        self.events = queue.Queue()
        self.reader = SerialReader("test-only-port", self.events)
        self.sample = dict(v=1, type="sample", seq=1, ms=500, who=0x70, address=0x68,
                           accel=[0, 0, 1], gyro=[0, 0, 0], errors=0)
        self.line = json.dumps(self.sample).encode() + b"\n"

    def run_devices(self, *devices):
        with patch("monitor.serial.Serial", side_effect=devices), \
                patch.object(self.reader.stop_event, "wait", return_value=False):
            self.reader.run()
        events = []
        while not self.events.empty():
            events.append(self.events.get_nowait()[:2])
        self.assertTrue(all(device.opened and device.closed for device in devices))
        return events

    def test_malformed_packets_do_not_stop_reception_or_leak_port(self):
        huge = json.dumps(dict(self.sample, accel=[10**400, 0, 1])).encode()
        device = FakeDevice(self.reader, [b"boot chatter\n", huge + b"\n", self.line])
        self.assertEqual(self.run_devices(device), [("open", None), ("message", self.sample)])

    def test_oversized_line_suffix_cannot_become_a_sample(self):
        device = FakeDevice(self.reader, [b"x" * 4096, b"x", self.line, self.line])
        self.assertEqual(self.run_devices(device), [("open", None), ("message", self.sample)])

    def test_reconnect_discards_partial_line_from_previous_device(self):
        first = FakeDevice(self.reader, [self.line[:20]], fail_at_end=True)
        second = FakeDevice(self.reader, [self.line])
        self.assertEqual(self.run_devices(first, second), [
            ("open", None), ("port_error", "simulated disconnect"),
            ("open", None), ("message", self.sample)])
