#include <Arduino.h>
#include <Wire.h>

// USB serial JSON Lines: 115200 baud, 20 samples/sec.
constexpr uint8_t SDA_PIN = 21, SCL_PIN = 22;
uint8_t address = 0, identity = 0;
uint32_t sequence = 0, errors = 0;

bool readRegisters(uint8_t addr, uint8_t reg, uint8_t* data, uint8_t count) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(addr, count, true) != count) return false;
  for (uint8_t i = 0; i < count; ++i) data[i] = Wire.read();
  return true;
}

bool configure(uint8_t addr, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(value);
  if (Wire.endTransmission() != 0) return false;
  uint8_t actual = 255;
  return readRegisters(addr, reg, &actual, 1) && actual == value;
}

void reportError(const char* code) {
  ++errors;
  Serial.printf("{\"v\":1,\"type\":\"error\",\"code\":\"%s\",\"errors\":%lu}\n", code, (unsigned long)errors);
}

bool initializeSensor() {
  for (uint8_t addr : {uint8_t(0x68), uint8_t(0x69)}) {
    uint8_t who = 0;
    if (!readRegisters(addr, 0x75, &who, 1)) continue;
    if (who != 0x68 && who != 0x70) continue;
    if (!configure(addr, 0x6B, 0x01)) continue; // wake, PLL clock
    delay(100);
    if (!configure(addr, 0x6C, 0x00) || // enable all axes
        !configure(addr, 0x1A, 0x03) || // gyro low-pass filter
        !configure(addr, 0x19, 0x09) || // internal 100 Hz
        !configure(addr, 0x1B, 0x00) || // +/-250 degrees/sec
        !configure(addr, 0x1C, 0x00)) continue; // +/-2 g
    if (who == 0x70 && !configure(addr, 0x1D, 0x03)) continue;
    address = addr;
    identity = who;
    return true;
  }
  return false;
}

int16_t signed16(const uint8_t* data) {
  return static_cast<int16_t>((static_cast<uint16_t>(data[0]) << 8) | data[1]);
}

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN, 100000);
  Wire.setTimeOut(50);
  delay(200);
}

void loop() {
  if (!address && !initializeSensor()) {
    reportError("sensor_not_ready");
    delay(1000);
    return;
  }
  uint8_t data[14], who = 0;
  if (!readRegisters(address, 0x75, &who, 1) || who != identity ||
      !readRegisters(address, 0x3B, data, 14)) {
    reportError("i2c_read_failed");
    address = 0;
    delay(100);
    return;
  }
  Serial.printf("{\"v\":1,\"type\":\"sample\",\"seq\":%lu,\"ms\":%lu,\"address\":%u,\"who\":%u,\"accel\":[%.5f,%.5f,%.5f],\"gyro\":[%.4f,%.4f,%.4f],\"errors\":%lu}\n",
    (unsigned long)++sequence, (unsigned long)millis(), address, identity,
    signed16(data)/16384.0, signed16(data+2)/16384.0, signed16(data+4)/16384.0,
    signed16(data+8)/131.0, signed16(data+10)/131.0, signed16(data+12)/131.0,
    (unsigned long)errors);
  delay(50);
}
