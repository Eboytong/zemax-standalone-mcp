# UserDefinedCOM factory repeat, 2026-11-08

- Item: `EX-01.UserDefinedCOM`; OpticStudio 24.2.0 build 240529; locally owned Standalone API session.
- Native probe: `PrimarySystem.Analyses.New_Analysis(AnalysisIDM.UserDefinedCOM)` using the installed enum value 161.
- Result: the formal factory returned `null`; no settings object, analysis result or native analysis handle was created. The probe made no assumptions about a COM class identifier and did not register or execute an unverified server.
- Lifecycle: there was no analysis handle to close; the owned OpticStudio application disconnected successfully.
- Command: `.venv\\Scripts\\python.exe -m pytest tests/native/test_userdefinedcom_factory_live.py -q --run-zemax` passed 1 probe test and wrote the raw record under `.local/runs/runs/userdefinedcom_factory_*/factory.json`.
- Blocker and release condition: provide a registered UserDefinedCOM server and its formal configuration/launch contract, or a native host context in which the API factory returns a valid object. Then inspect settings, execute, result outlet and server/application termination.
- Completion count: 0.
