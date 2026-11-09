# C callback contract repeat, 2026-11-08

- Item: `EX-01.CCallback`; OpticStudio 24.2.0 build 240529 PremiumEdition, local installed API reflection and official 2024 R2 interface reference.
- Official native contract: `IZOSAPI_Application.LoadCCallback(string cLib, string callbackName, ISettingsData settings)` returns `IZOSAPI_Callback`. The callback interface exposes `Execute()` and `Copy(app)`; the official interface derives from `IDisposable`.
- Local evidence: `development/evidence/EX-01/probe036.json` contains the installed application method signature and callback interface members. `development/evidence/EX-01/contract-followup045.json` records inheritance and notes the missing exported function ABI and native execution.
- Scope reached: method and managed lifetime contract confirmed. No local controlled C callback DLL or documented exported function signature is available. No DLL was built with a guessed ABI or loaded. Consequently settings adoption, `Execute` return, error behavior, cancellation, and actual disposal remain unverified.
- Checks: read-only inspection of local reflection records and installed resources; no native callback call was made because a valid function signature/fixture is absent.
- Blocker and release condition: obtain the vendor's C callback export ABI and a compatible test fixture, then run an isolated `LoadCCallback`/settings/`Execute`/`Dispose` test and verify application shutdown.
- Completion count: 0.
