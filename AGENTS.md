# Development

Keep this a minimal Windows desktop sensor monitor. Preserve firmware/protocol compatibility.
Use an Issue and a feature/fix branch, then a PR with passing CI before merging. Never push directly to the default branch, force push, or bypass protections. Protect unrelated changes. Do not commit credentials, private paths, device identifiers or local logs.

Checks:
- `python -m unittest discover -s tests -v`
- `python -m compileall -q monitor.py protocol.py tests`
- `arduino-cli compile --fqbn esp32:esp32:esp32 firmware/mpu_monitor`
- `arduino-cli compile --fqbn esp32:esp32:esp32 diagnostics/mpu_diagnostic`

Hardware claims require a real hardware test. CI cannot verify wiring. Do not flash other hardware without authorization. Preserve SDA=21/SCL=22 and label WHO_AM_I=0x70 as MPU6500-compatible.
See docs/development-workflow.md for setup status. After three meaningful failed attempts at the same unresolved problem, record hypotheses and outcomes in the Issue and mark it Blocked; continue independent work.
