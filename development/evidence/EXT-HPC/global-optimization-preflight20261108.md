# HPC global optimization preflight, 2026-11-08

- Item: `EXT-HPC.GlobalOptimization`; OpticStudio 24.2.0 build 240529 PremiumEdition.
- Plan: inspect the typed global optimization/HPC path, run focused unit tests, then use real stdio to query preferences before any model or optimization mutation; if settings are unavailable, capture the original error and close the session.
- Ordinary checks: `.venv\Scripts\python.exe -m pytest tests/unit/test_hpc.py tests/unit/test_hpc_execution.py -q` passed 34 tests.
- Native check: `.venv\Scripts\python.exe -m pytest 'tests/native/test_hpc_live.py::test_hpc_minimal_native_job_result_and_close[global]' -q --run-zemax` reported 1 skipped in 12.89 s after the explicit preflight. The test now treats a null native preferences object as an environment prerequisite, disconnects, and skips instead of misreporting it as an optimization failure.
- Captured sequence: `connect` succeeded; `get_hpc_settings(request={mode: preferences})` returned `HPC_SETTINGS_UNAVAILABLE`, native method `GetHPCSettingsFromPrefs`, `partial_changes_possible=false`, model revision 0; no model was opened and no optimization job was created; `disconnect` succeeded with `connected=false`. No Python or OpticStudio process remained.
- Conclusion: the typed command and task adapter are present, but the current machine cannot enter the native HPC job path. Keep `已实现待验收`. Unlock condition: configure preferences so `GetHPCSettingsFromPrefs` returns a non-null, configured `IHPCSettings`, then verify node/feature access, queue state, cancellation, result collection and independent optimization validation.
- Run evidence: `.local/runs/runs/hpc_global_b4c8326146/calls.json`.
- Completion count: 0.
