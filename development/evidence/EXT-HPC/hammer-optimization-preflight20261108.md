# HPC Hammer optimization preflight, 2026-11-08

- Item: `EXT-HPC.HammerOptimization`; OpticStudio 24.2.0 build 240529 PremiumEdition.
- Plan: reuse the shared HPC adapter unit checks and run the Hammer-specific real-stdio entry through its preflight; capture the native response, model revision, task creation boundary and disconnect.
- Shared ordinary checks: `tests/unit/test_hpc.py` and `tests/unit/test_hpc_execution.py` passed 34 tests in the preceding `EXT-HPC.GlobalOptimization` check; these cover both `OpenHammerOptimization_HPC` and the common configured/unconfigured preflight.
- Native check: `.venv\Scripts\python.exe -m pytest 'tests/native/test_hpc_live.py::test_hpc_minimal_native_job_result_and_close[hammer]' -q --run-zemax` reported 1 skipped in 13.02 s after preflight.
- Captured sequence: `connect` succeeded; preferences query returned `HPC_SETTINGS_UNAVAILABLE` from `GetHPCSettingsFromPrefs`, with `partial_changes_possible=false` and model revision 0; no model was opened and no Hammer tool/task was created; explicit `disconnect` succeeded. No Python or OpticStudio process remained.
- Conclusion: keep `已实现待验收`. Unlock condition: a valid configured preferences object, node allocation and required feature access; then verify queue/status, cancellation, result and independent candidate validation.
- Run evidence: `.local/runs/runs/hpc_hammer_e5b2191e4c/calls.json`.
- Completion count: 0.
