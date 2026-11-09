# PathAnalysis Threshold-Excluded Flux Repeat

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14.

Checks run:

- `.venv\Scripts\python.exe -m pytest tests/unit/test_path_analysis.py -q`: 36 passed.
- `.venv\Scripts\python.exe -m pytest tests/native/test_nsc_paths_reference_live.py::test_path_uncategorized_flux_against_independent_database_sum -q --run-zemax`: failed at the intended threshold-1 assertion after 18.43 s.

The controlled NSC model used a 10-ray SourceRay, N-BK7 rectangular volume, detector, and an owned ZRD. The independent ZRD segment sum at the detector was required and observed within `(0.8, 0.99) W`. At threshold 0, classified paths account for the reference and native uncategorized is absent. At threshold 1, all classified rows are filtered, while native `GetPathUncategorized()` reports exactly `There are no uncategorized paths.` The test therefore fails its requirement that the removed power be returned as an uncategorized path.

The test harness close receipt records checkpoint save `ok=true`, native close `closed=true`, and normal session closure; `requires_reconnect=false`. Raw run directory: `.local/runs/runs/paths063_uncategorized_80ef223bc9/`; relevant files include `loss.zrd`, `calls.json`, `checks.json`, and `state/close_receipt.json`.

The adapter preserves the native message and does not synthesize missing power. The remaining condition is a vendor-defined threshold-excluded flux result or a documented native contract that identifies the excluded power category.
