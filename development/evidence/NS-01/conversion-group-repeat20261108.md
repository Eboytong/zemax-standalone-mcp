# NS-01 mixed group conversion repeat, 2026-11-08

- Item: `NS-01.Conversion`; OpticStudio 24.2.0 build 240529 PremiumEdition; controlled air 2 mm / N-BK7 plane plate 2 mm / air 2 mm model.
- Plan: run conversion unit checks and the mixed-group polarized plane reference with stop-to-aperture conversion disabled and global coordinates enabled; inspect the native error, close behavior, checkpoint restore, sequential ray recovery, and final disconnect.
- Ordinary check: `.venv\Scripts\python.exe -m pytest tests/unit/test_conversion.py -q` passed 22 tests.
- Native check: `.venv\Scripts\python.exe -m pytest 'tests/native/test_conversion_optical_reference_live.py::test_conversion_polarized_plane_reference[group]' -q --run-zemax -rxX` reported 1 expected failure in 17.48 s. The failure is the explicit recorded native limitation, not an assertion regression.
- Request/readback: group mode, surfaces 1-4, `ConvertStopToNSCAperture=false`, `ConvertToGlobalCoordinates=true`, `CreateSourcesAndDetectors=false`, `IgnoreErrors=false`; native task readback reported `IsValid=true`, `Succeeded=false`, `CanCancel=false`.
- Native result: `TASK_START_FAILED`, message `An unknown error occurred`, `partial_changes_possible=true`; task reached `failed`, `close_attempted=true`, `requires_reconnect=false`. The test opened the emitted checkpoint and compared the restored surfaces and direct sequential rays against baseline.
- Recovery/reference: 187 post-failure checks passed with zero failed comparisons; the checkpoint re-trace task succeeded. The separate pure-conversion reference remains the previous controlled 379-check pass (maximum ray error `2.815423927327032e-08`) from `development/evidence/NS-01/progress282.json`.
- Lifecycle: stdio disconnect succeeded; native close receipt reports `attempted=true`, `closed=true`, `error=null`; no OpticStudio/Python process remained.
- Conclusion: keep `已实现待验收`. Mixed group conversion has no usable result to compare. Unlock condition: reliable native group conversion path or corrected OpticStudio build; rerun the controlled optical equivalence, settings/persistence and cleanup checks. Run folder: `.local/runs/runs/conversion277_group_6e7b98bacf/`.
- Completion count: 0.
