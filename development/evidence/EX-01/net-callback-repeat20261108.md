# .NET callback repeat, 2026-11-08

- Item: `EX-01.NETCallback`; OpticStudio 24.2.0 build 240529; controlled `ScalarCallback` fixture built with the installed .NET Framework x64 compiler and installed 2024 R2 ZOSAPI assemblies.
- Path correction: `tests/support/net_callback_fixture.py` previously looked for `fixtures/net_callback/ScalarCallback.cs` at repository root. The source is under `tests/fixtures/net_callback`; the builder now targets the checked-in fixture location.
- Command: `.venv\\Scripts\\python.exe -m pytest tests/native/test_net_callback_live.py -q --run-zemax`.
- Build: compiler returned 0 and produced `net-callback.dll` for type `ZemaxMcp.Fixtures.ScalarCallback`.
- Native outcome: application connection succeeded, but `LoadNETCallback` returned `null` for that assembly/type/settings. Settings adoption, Execute output and callback disposal could not be exercised because no handle was returned.
- Lifecycle: the test's `finally` disconnected the native application (`closed=true`); there were no cleanup errors. `callback_disposed=false` reflects the absent handle.
- Blocker and release condition: determine the supported assembly/type/load contract or obtain a vendor-compatible working fixture; then verify input/output settings, Execute return, IDisposable cleanup and application shutdown.
- Completion count: 0.
