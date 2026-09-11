"""Validate serial messages; ignore boot chatter and reject malformed data."""
import json
import math


def parse_message(line):
    try:
        message = json.loads(line)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(message, dict) or message.get("v") != 1:
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
        if any(type(v) not in (float, int) or not math.isfinite(v) for v in values):
            return None
    return message


def stream_status(last_sample, now, sensor_error=False):
    if sensor_error:
        return "sensor_error"
    if last_sample is None:
        return "waiting"
    return "stale" if now - last_sample > 1.0 else "live"
