#include <Arduino.h>
#include <Wire.h>

bool readRegs(uint8_t addr, uint8_t reg, uint8_t* out, uint8_t n) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(addr, n, true) != n) return false;
  for (uint8_t i = 0; i < n; ++i) out[i] = Wire.read();
  return true;
}
bool writeReg(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr); Wire.write(reg); Wire.write(val);
  return Wire.endTransmission() == 0;
}
uint8_t sensor = 0;
unsigned long sample = 0;
int16_t s16(const uint8_t* p) { return (int16_t)(((uint16_t)p[0] << 8) | p[1]); }
void setup() {
  Serial.begin(115200);
  delay(1500);
  Wire.begin(21, 22, 100000);
  Wire.setTimeOut(100);
  Serial.println("MPU6XXX_DIAGNOSTIC SDA=21 SCL=22 I2C=100000 UART=115200");
  for (uint8_t a=1; a<127; ++a) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission()==0) Serial.printf("I2C_ACK address=0x%02X\n",a);
  }
  for (uint8_t a : {uint8_t(0x68), uint8_t(0x69)}) {
    uint8_t who=0;
    if (readRegs(a,0x75,&who,1)) {
      Serial.printf("WHO_AM_I address=0x%02X value=0x%02X accepted=0x68(MPU6050),0x70(MPU6500)\n",a,who);
      if ((who==0x68 || who==0x70) && !sensor) sensor=a;
    }
  }
  if (!sensor) { Serial.println("FAIL SUPPORTED_MPU_NOT_IDENTIFIED"); return; }
  bool ok = writeReg(sensor,0x6B,0x01);
  delay(100);
  ok = writeReg(sensor,0x1B,0x00) && ok;
  ok = writeReg(sensor,0x1C,0x00) && ok;
  uint8_t pwr=255;
  ok = readRegs(sensor,0x6B,&pwr,1) && ok;
  Serial.printf("INIT %s PWR_MGMT_1=0x%02X\n",ok && !(pwr&0x40)?"OK":"FAIL",pwr);
}
void loop() {
  if (!sensor) { Serial.println("FAIL SUPPORTED_MPU_NOT_IDENTIFIED"); delay(1000); return; }
  uint8_t b[14],who=0;
  if (!readRegs(sensor,0x75,&who,1) || !readRegs(sensor,0x3B,b,14)) {
    Serial.println("FAIL I2C_READ");
  } else {
    Serial.printf("SAMPLE %lu WHO=0x%02X ACCEL_G=%.4f,%.4f,%.4f GYRO_DPS=%.3f,%.3f,%.3f TEMP_RAW=%d\n",
      ++sample,who,s16(b)/16384.0,s16(b+2)/16384.0,s16(b+4)/16384.0,
      s16(b+8)/131.0,s16(b+10)/131.0,s16(b+12)/131.0,s16(b+6));
  }
  delay(1000);
}
