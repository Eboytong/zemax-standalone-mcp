# HPC tolerancing preflight, 2026-11-08

- Item: `EXT-HPC.Tolerancing`; OpticStudio 24.2.0 build 240529 PremiumEdition.
- Plan: reuse shared HPC unit coverage and run the tolerance-specific native entry through settings preflight; verify no tolerance tool is opened before an HPC object is available.
- Ordinary checks: shared HPC unit tests passed 34 cases in the GlobalOptimization check, including tolerance HPC factory selection, configuration validation and failed-setup cleanup.
- Native check: `.venv\Scripts\python.exe -m pytest 'tests/native/test_hpc_live.py::test_hpc_minimal_native_job_result_and_close[tolerance]' -q --run-zemax` reported 1 skipped in 12.86 s after preflight.
- Captured sequence: stdio `connect` succeeded; `GetHPCSettingsFromPrefs` returned `HPC_SETTINGS_UNAVAILABLE`, `partial_changes_possible=false`, model revision 0; no lens/tolerance task was opened; explicit `disconnect` succeeded. No Python or OpticStudio process remained.
- Conclusion: keep `已实现待验收`. Unlock condition: valid configured HPC preferences, node allocation and feature access; then run the controlled four-sample tolerance case, verify queue/cancellation/result and compare summary to its local reference.
- Run evidence: `.local/runs/runs/hpc_tolerance_050d84f49e/calls.json`.
- Completion count: 0.
