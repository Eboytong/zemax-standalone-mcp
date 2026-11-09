# Register operand callback repeat, 2026-11-08

- Item: `EX-01.RegisterOperandCallback`; OpticStudio 24.2.0 build 240529; controlled `ScalarCallback` x64 assembly compiled against installed 2024 R2 ZOSAPI assemblies.
- Native call: `RegisterNETOperandCallback(path, "ZemaxMcp.Fixtures.ScalarCallback", settings)` with a double `input=1.5` setting.
- Result: call returned a non-null `ZOSAPI.Analysis.Message`; its `Text` property was exactly `This is not a UDOC!`. This proves the formal registration entry is callable and rejects the current fixture as the wrong callback class. No operand was registered or evaluated, so no MFE result or unregister behavior was exercised.
- Lifecycle: native application disconnected successfully; no cleanup error. Registration is performed in an isolated process/session.
- Command: `.venv\\Scripts\\python.exe -m pytest tests/native/test_register_operand_callback_live.py -q --run-zemax` passed 1 probe test after adding an exact assertion for the native rejection message.
- Blocker and release condition: obtain or build a fixture implementing the official UDOC callback contract, then verify registration success, operand values through MFE evaluation, and application-scoped teardown. The full application interface has no unregister endpoint in the current reflection record, so cleanup must be validated by closing the owning application.
- Completion count: 0.
