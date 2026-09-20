"""Validate serial messages; ignore boot chatter and reject malformed data."""
import json
import math

MAX_LINE_BYTES = 4096


def parse_message(line):
    try:
        message = json.loads(line)
    except (ValueError, UnicodeDecodeError, RecursionError):
        return None
    if not isinstance(message, dict) or type(message.get("v")) is not int or message["v"] != 1:
        return None
    kind = message.get("type")
    if kind not in ("sample", "error"):
        return None
    if type(message.get("errors")) is not int or message["errors"] < 0:
        return None
    if kind == "error":
        return message if isinstance(message.get("code"), str) else None
    for key in ("seq", "ms", "address", "who"):
        if type(message.get(key)) is not int or message[key] < 0:
            return None
    if message["who"] not in (0x68, 0x70) or message["address"] not in (0x68, 0x69):
        return None
    for key in ("accel", "gyro"):
        values = message.get(key)
        if not isinstance(values, list) or len(values) != 3:
            return None
        try:
            if any(type(v) not in (float, int) or not math.isfinite(v) for v in values):
                return None
        except OverflowError:
            return None
    return message


class MessageStream:
    """Decode bounded JSON lines without accepting an oversized line's suffix."""

    def __init__(self):
        self.buffer = bytearray()
        self.discarding = False

    def feed(self, chunk):
        messages = []
        fragments = chunk.split(b"\n")
        for index, fragment in enumerate(fragments):
            if not self.discarding:
                if len(self.buffer) + len(fragment) > MAX_LINE_BYTES:
                    self.buffer.clear()
                    self.discarding = True
                else:
                    self.buffer.extend(fragment)
            if index < len(fragments) - 1:
                if not self.discarding:
                    message = parse_message(self.buffer)
                    if message is not None:
                        messages.append(message)
                self.buffer.clear()
                self.discarding = False
        return messages


def stream_status(last_sample, now, sensor_error=False):
    if sensor_error:
        return "sensor_error"
    if last_sample is None:
        return "waiting"
    return "stale" if now - last_sample > 1.0 else "live"
