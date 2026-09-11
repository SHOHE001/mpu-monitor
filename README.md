# MPU Monitor

ESP32に接続したMPU6050 / MPU6500相当のセンサーをWindowsで見る、小さなデスクトップアプリです。

- 加速度XYZ（g）、ジャイロXYZ（°/s）、直近10秒の波形
- 約15〜20Hz更新、接続・データ途絶・センサー通信エラー表示
- USB切断時は同じCOMポートへの再接続を試行
- 識別値0x68をMPU6050相当、0x70をMPU6500相当として表示

## 配線

電源を外して配線してください。

| センサー | ESP32 |
| --- | --- |
| VCC | 3.3V |
| GND | GND |
| SDA | GPIO21 |
| SCL | GPIO22 |

対象は標準ESP32（検証機ESP32-D0WD-V3、4MBフラッシュ）。他のESP32系ボードではピンとビルド対象を確認してください。

## Windowsで使う

1. Python 3.13（Tkinterを含む）をインストールし、このフォルダーを展開。
2. 初回だけ `setup.bat` を実行（pySerial 3.5を専用 `.venv` に導入）。
3. ESP32へ下記ファームウェアを書き込み、USB接続。
4. `start.bat` を開き、COMポートを選んで「接続」。
5. 「受信中」とXYZの値が表示されます。「切断」またはウィンドウを閉じるとポートを解放します。

ポートが見つからない場合は「更新」。Arduinoのシリアルモニターなど同じポートを使うアプリは閉じてください。COM番号が変わった場合は一度「切断」し、新しい番号を選びます。

## ファームウェア

Arduino IDEではESP32 core **3.3.11**、ボード **ESP32 Dev Module** を選び、`firmware/mpu_monitor/mpu_monitor.ino` を書き込みます。外部センサーライブラリは不要です。

Arduino CLI:

```sh
arduino-cli core update-index --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core install esp32:esp32@3.3.11 --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli compile --fqbn esp32:esp32:esp32 --output-dir build firmware/mpu_monitor
arduino-cli upload --fqbn esp32:esp32:esp32 --port COM3 --input-dir build firmware/mpu_monitor
```

COM3は例です。書き込みは既存アプリを置き換えます。通常の閲覧では再書き込みは不要です。

## 読み方と制限

- 加速度には重力を含みます。静止状態の合計は約1gが目安です。
- ジャイロは未校正で、静止中にもゼロ点ずれがあります。精密な角度計測用ではありません。
- 波形の縦軸は自動調整。数値と目盛りを合わせて確認してください。
- 1秒以上サンプルが届かない場合やエラー時は数値を消します。グラフには過去10秒の履歴が残ります。
- エラー回数はESP32起動後の累積。USB切断自体はこのカウンターに含みません。
- 検証機は基板表示がMPU6050でも識別値は0x70でした。識別値だけで真正性や正確な型番までは保証できません。
- PCからは読み取りのみ。記録・ネットワーク・姿勢推定・校正機能はありません。

`diagnostics/mpu_diagnostic/` は初期調査のI2Cスキャン・低速読み取りコードです。GUI用JSON形式ではありません。GUIには `firmware/mpu_monitor/` を書き込んでください。

[通信仕様](docs/protocol.md) / [検証結果](docs/verification.md) / [開発手順](docs/development-workflow.md)
