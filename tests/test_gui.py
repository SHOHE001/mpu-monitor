"""GUI error and recovery behavior without connected hardware."""
import queue
import time
import unittest
try:
    import tkinter as tk
    from monitor import Monitor
except ImportError:
    tk = None


@unittest.skipIf(tk is None, 'Tkinter and pySerial required')
class GuiTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = Monitor(self.root)
        self.app.reader = object()  # Feed only explicit test events.

    def tearDown(self):
        self.app.reader = None
        self.app.close()

    def sample(self):
        self.app.events.put(('message', dict(type='sample', who=0x70, address=0x68,
                            accel=[0, 0, 1], gyro=[0, 0, 0], errors=0), time.monotonic()))
        self.app.tick()

    def test_sensor_error_clears_values_and_valid_sample_recovers(self):
        self.sample()
        self.app.events.put(('message', dict(type='error', errors=1), time.monotonic()))
        self.app.tick()
        self.assertIn('センサー通信エラー', self.app.status.cget('text'))
        self.assertTrue(all('—' in x.cget('text') for group in self.app.values for x in group))
        self.sample()
        self.assertIn('受信中', self.app.status.cget('text'))
        self.assertIn('+1.000', self.app.values[0][2].cget('text'))

    def test_stale_and_port_failure_are_not_live(self):
        self.sample()
        self.app.last_sample = time.monotonic() - 2
        self.app.tick()
        self.assertIn('途絶', self.app.status.cget('text'))
        self.app.events.put(('port_error', 'unplugged', time.monotonic()))
        self.app.tick()
        self.assertIn('USB接続エラー', self.app.status.cget('text'))
        self.app.events.put(('open', None, time.monotonic()))
        self.app.tick()
        self.assertIn('データ待ち', self.app.status.cget('text'))
        self.sample()
        self.assertIn('受信中', self.app.status.cget('text'))
