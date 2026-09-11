"""Small Windows desktop monitor for the accompanying ESP32 firmware."""
import argparse
from collections import deque
import math
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk

import serial
from serial.tools import list_ports

from protocol import parse_message, stream_status

BG, PANEL, FG, MUTED = "#111827", "#1f2937", "#f3f4f6", "#9ca3af"
COLORS = ("#60a5fa", "#34d399", "#fbbf24")


class SerialReader(threading.Thread):
    def __init__(self, port, events):
        super().__init__(daemon=True)
        self.port, self.events = port, events
        self.stop_event = threading.Event()

    def emit(self, kind, value=None):
        try:
            self.events.put_nowait((kind, value, time.monotonic()))
        except queue.Full:
            pass

    def run(self):
        while not self.stop_event.is_set():
            try:
                with serial.Serial(port=None, baudrate=115200, timeout=0.2) as device:
                    device.dtr = False
                    device.rts = False
                    device.port = self.port
                    device.open()
                    self.emit("open")
                    buffer = bytearray()
                    while not self.stop_event.is_set():
                        buffer.extend(device.read(min(max(device.in_waiting, 1), 4096)))
                        while b"\n" in buffer:
                            raw, _, rest = buffer.partition(b"\n")
                            buffer = bytearray(rest)
                            msg = parse_message(raw)
                            if msg:
                                self.emit("message", msg)
                        if len(buffer) > 4096:
                            buffer.clear()
            except (serial.SerialException, OSError) as exc:
                self.emit("port_error", str(exc))
            if self.stop_event.wait(1):
                break


class Plot(tk.Canvas):
    def __init__(self, parent, title, unit, minimum):
        super().__init__(parent, bg=PANEL, highlightthickness=0, height=175)
        self.title, self.unit, self.minimum = title, unit, minimum

    def draw(self, points, now):
        self.delete("all")
        width, height = max(self.winfo_width(), 200), max(self.winfo_height(), 150)
        left, right, top, bottom = 58, width - 20, 38, height - 28
        limit = max(self.minimum, max((abs(v) for _, values in points for v in values), default=0) * 1.15)
        self.create_text(15, 17, anchor="w", text=f"{self.title}  /  {self.unit}", fill=FG, font=("Yu Gothic UI", 11, "bold"))
        for i, axis in enumerate("XYZ"):
            self.create_text(right - 100 + i * 40, 17, text=axis, fill=COLORS[i])
        for factor in (-1, 0, 1):
            y = (top + bottom) / 2 - factor * (bottom - top) / 2
            self.create_line(left, y, right, y, fill="#374151")
            self.create_text(left - 7, y, text=f"{factor*limit:.1f}", fill=MUTED, anchor="e")
        self.create_text(left, height - 12, text="−10秒", fill=MUTED, anchor="w")
        self.create_text(right, height - 12, text="現在", fill=MUTED, anchor="e")
        for axis, color in enumerate(COLORS):
            coords, previous = [], None
            for stamp, values in points:
                if stamp < now - 10:
                    continue
                if previous is not None and stamp - previous > 0.3:
                    if len(coords) >= 4:
                        self.create_line(*coords, fill=color, width=2)
                    coords = []
                x = right - (now - stamp) / 10 * (right - left)
                y = (top + bottom) / 2 - values[axis] / limit * (bottom - top) / 2
                coords.extend((x, y))
                previous = stamp
            if len(coords) >= 4:
                self.create_line(*coords, fill=color, width=2)


class Monitor:
    def __init__(self, root, port=None):
        self.root, self.reader = root, None
        self.events = queue.Queue(maxsize=500)
        self.last_sample, self.sensor_error, self.port_error = None, False, None
        self.accel, self.gyro, self.times = deque(maxlen=250), deque(maxlen=250), deque(maxlen=250)
        self.received, self.error_count = 0, 0
        root.title("MPU Monitor")
        root.geometry("860x690")
        root.minsize(680, 610)
        root.configure(bg=BG)
        root.protocol("WM_DELETE_WINDOW", self.close)
        top = tk.Frame(root, bg=BG)
        top.pack(fill="x", padx=24, pady=(20, 12))
        tk.Label(top, text="MPU Monitor", fg=FG, bg=BG, font=("Segoe UI", 22, "bold")).pack(side="left")
        self.port = tk.StringVar(value=port or "")
        self.ports = ttk.Combobox(top, textvariable=self.port, width=10, state="readonly")
        self.ports.pack(side="left", padx=(25, 8))
        ttk.Button(top, text="更新", command=self.refresh_ports).pack(side="left")
        self.button = ttk.Button(top, text="接続", command=self.toggle)
        self.button.pack(side="left", padx=8)
        self.status = tk.Label(root, text="未接続", bg=BG, fg=MUTED, anchor="w", font=("Yu Gothic UI", 12, "bold"))
        self.status.pack(fill="x", padx=24)
        self.info = tk.Label(root, text="USBでESP32を接続し、ポートを選択してください", bg=BG, fg=MUTED, anchor="w")
        self.info.pack(fill="x", padx=24, pady=(5, 12))
        numbers = tk.Frame(root, bg=BG)
        numbers.pack(fill="x", padx=24)
        self.values = []
        for col, title in enumerate(("加速度  /  g", "ジャイロ  /  °/s")):
            cell = tk.Frame(numbers, bg=PANEL, padx=16, pady=12)
            cell.grid(row=0, column=col, sticky="ew", padx=(0, 8) if col == 0 else (8, 0))
            numbers.columnconfigure(col, weight=1)
            tk.Label(cell, text=title, bg=PANEL, fg=MUTED, anchor="w").pack(fill="x")
            axes = []
            for axis, color in zip("XYZ", COLORS):
                label = tk.Label(cell, text=f"{axis}    —", bg=PANEL, fg=color, anchor="w", font=("Consolas", 17))
                label.pack(fill="x")
                axes.append(label)
            self.values.append(axes)
        # Reserve the status footer before expandable plots, including at minimum size.
        self.footer = tk.Label(root, text="加速度は重力を含みます。ジャイロは未校正です。", bg=BG, fg=MUTED, anchor="w")
        self.footer.pack(side="bottom", fill="x", padx=24, pady=12)
        self.plots = (Plot(root, "加速度", "g", 1.2), Plot(root, "ジャイロ", "°/s", 5))
        for plot in self.plots:
            plot.pack(fill="both", expand=True, padx=24, pady=(12, 0))
        self.refresh_ports()
        self.root.after(50, self.tick)
        if port:
            self.root.after(100, self.toggle)

    def refresh_ports(self):
        ports = [p.device for p in list_ports.comports()]
        self.ports["values"] = ports
        if not self.port.get() and ports:
            self.port.set(ports[0])

    def clear_values(self):
        for labels in self.values:
            for axis, label in zip("XYZ", labels):
                label.configure(text=f"{axis}    —")

    def toggle(self):
        if self.reader:
            self.reader.stop_event.set()
            self.reader.join(timeout=1.5)
            if self.reader.is_alive():
                self.status.configure(text="切断処理中です…", fg=COLORS[2])
                return
            self.reader = None
            self.button.configure(text="接続")
            self.ports.configure(state="readonly")
            self.clear_values()
            self.status.configure(text="未接続", fg=MUTED)
            self.info.configure(text="接続を終了しました")
            return
        if not self.port.get():
            self.status.configure(text="COMポートを選択してください", fg=COLORS[2])
            return
        self.events = queue.Queue(maxsize=500)
        self.accel.clear(); self.gyro.clear(); self.times.clear()
        self.last_sample, self.sensor_error, self.port_error = None, False, None
        self.received, self.error_count = 0, 0
        self.reader = SerialReader(self.port.get(), self.events)
        self.reader.start()
        self.button.configure(text="切断")
        self.ports.configure(state="disabled")
        self.info.configure(text="センサーの応答を待っています")

    def tick(self):
        now = time.monotonic()
        if self.reader:
            while True:
                try:
                    kind, value, stamp = self.events.get_nowait()
                except queue.Empty:
                    break
                if kind == "port_error":
                    self.port_error = value
                    self.info.configure(text="USB接続と、他のアプリがCOMポートを使用していないか確認してください")
                elif kind == "open":
                    self.port_error = None
                    self.last_sample = None
                    self.sensor_error = False
                elif kind == "message":
                    self.error_count = value["errors"]
                    self.sensor_error = value["type"] == "error"
                    if self.sensor_error:
                        self.info.configure(text="センサーへの通信に失敗しました。電源・SDA・SCLの接続を確認してください")
                    else:
                        self.last_sample = stamp
                        self.received += 1
                        self.times.append(stamp)
                        self.accel.append((stamp, value["accel"]))
                        self.gyro.append((stamp, value["gyro"]))
                        for labels, key in zip(self.values, ("accel", "gyro")):
                            for axis, label, number in zip("XYZ", labels, value[key]):
                                label.configure(text=f"{axis}  {number:+9.3f}")
                        model = "MPU6500相当" if value["who"] == 0x70 else "MPU6050相当"
                        norm = math.sqrt(sum(v*v for v in value["accel"]))
                        self.info.configure(text=f"{model}  ·  ID 0x{value['who']:02X}  ·  I²C 0x{value['address']:02X}  ·  加速度合計 {norm:.3f} g")
            state = stream_status(self.last_sample, now, self.sensor_error)
            labels = {"waiting": "接続中・データ待ち", "live": "●  受信中", "stale": "データ途絶（1秒以上）", "sensor_error": "センサー通信エラー"}
            text = "USB接続エラー・再接続待ち" if self.port_error else labels[state]
            self.status.configure(text=text, fg=COLORS[1] if state == "live" and not self.port_error else COLORS[2])
            if state != "live" or self.port_error:
                self.clear_values()
            recent = [t for t in self.times if now - t <= 2]
            hz = (len(recent)-1)/(recent[-1]-recent[0]) if len(recent) > 1 else 0
            if state != "live" or self.port_error:
                hz = 0
            self.footer.configure(text=f"{hz:.1f} Hz  ·  受信 {self.received}件  ·  センサーエラー {self.error_count}回（ESP32起動後）  |  重力込み・未校正")
        for plot, points in zip(self.plots, (self.accel, self.gyro)):
            plot.draw(points, now)
        self.root.after(50, self.tick)

    def close(self):
        if self.reader:
            self.reader.stop_event.set()
            self.reader.join(timeout=1.5)
        self.root.destroy()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="COM port to connect on startup")
    args = parser.parse_args()
    root = tk.Tk()
    Monitor(root, args.port)
    root.mainloop()
