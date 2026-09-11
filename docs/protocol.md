# 通信仕様

USBシリアル115200bps、8N1、UTF-8 JSON Lines。PCからのコマンド送信なし。v=1。

正常時は約50ms間隔で送信。I2C・送信処理時間により実効レートは20Hzよりわずかに低くなります。

```json
{"v":1,"type":"sample","seq":1,"ms":250,"address":104,"who":112,"accel":[0.0,0.0,1.0],"gyro":[0.0,0.0,0.0],"errors":0}
```

seq/ms/errorsはESP32起動後。msは32bitのmillis()で周回します。PCは波形と途絶判定にPCの単調増加時計を使います。accelはg、gyroは°/s。±2g / ±250°/sの設定をレジスタの読み返しで確認します。

```json
{"v":1,"type":"error","code":"i2c_read_failed","errors":1}
```

sensor_not_readyは未検出・未対応識別値・初期化失敗。i2c_read_failedは読み取り失敗または識別値不一致。失敗後は再初期化を試行。

PCは不正JSON・ブートログ・未対応バージョン・非有限数・不正配列を表示対象から除外します。

参照:
- [Espressif Wire API](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/i2c.html)
- [pySerial API](https://pyserial.readthedocs.io/en/latest/pyserial_api.html)
- [TDK MPU6050 register map](https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Register-Map1.pdf)
- [TDK MPU6500 register map](https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6500-Register-Map2.pdf)
