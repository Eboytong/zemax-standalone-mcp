# HPC NSC trace preflight, 2026-11-08

- Item: `EXT-HPC.NSCTrace`; OpticStudio 24.2.0 build 240529 PremiumEdition.
- Plan: reuse the shared HPC adapter checks; run the NSC-specific native job path through preference preflight and confirm no detector/tool mutation occurs when native settings are unavailable.
- Ordinary checks: shared `.venv\Scripts\python.exe -m pytest tests/unit/test_hpc.py tests/unit/test_hpc_execution.py -q` passed 34 tests; these include HPC NSC factory selection, configuration checks and cleanup ordering.
- Native check: `.venv\Scripts\python.exe -m pytest 'tests/native/test_hpc_live.py::test_hpc_minimal_native_job_result_and_close[nsc]' -q --run-zemax` reported 1 skipped in 12.98 s after preflight.
- Captured sequence: `connect` succeeded; `GetHPCSettingsFromPrefs` returned `HPC_SETTINGS_UNAVAILABLE` with `partial_changes_possible=false`, model revision 0; no NSC trace tool, detector clear or object mutation was reached; `disconnect` succeeded. No Python or OpticStudio process remained.
- Conclusion: keep `已实现待验收`. Unlock condition: valid configured HPC preferences, node allocation and feature access; then run the controlled 10-ray detector model and compare its 1 W result, queue, cancellation and retrieval.
- Run evidence: `.local/runs/runs/hpc_nsc_e100e36be9/calls.json`.
- Completion count: 0.
