# Speos Whitebox Export Acceptance

- Environment: OpticStudio 24.2.0 build 240529 PremiumEdition, Python 3.14.
- Plan: execute the typed Whitebox export using the Cooke lens and inspect native output identity, error code, support files, source state and cleanup.
- Native command: `pytest tests/native/test_speos_live.py::test_speos_owned_copy_native -m zemax --run-zemax -k whitebox -q -s` — 1 passed, 2 deselected.
- Request: Whitebox export to a newly created absolute directory under `.local/runs/runs/speos_whitebox_546c939a28/whitebox`.
- Result: task `succeeded`; native `OutputFilename` matched `input.odx`; `ErrorCode=0`. Outputs were `input.odx`, `input.odx.log`, and `input.ZDA`.
- Source preservation: the native test compared system settings and surface data before and after the export; both matched. Result metadata also reported `source_metadata_preserved=true`.
- Lifecycle: export tool and copied system reported closed; stdio disconnect succeeded.
- Receiver import remains a separate blocked operation because no runnable Speos receiver was identified locally. Unlock by providing a receiver installation and validating imported geometry, units, and referenced files.
- Run record: `.local/runs/runs/speos_whitebox_546c939a28/calls.json` and task result JSON.
