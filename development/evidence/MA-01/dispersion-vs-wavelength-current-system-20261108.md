# DispersionvsWavelength Current-System Acceptance

- Environment: OpticStudio 24.2.0 build 240529 PremiumEdition, Python 3.14.
- Supported scope: typed kind-only request for the native current-system `dn/dlambda` report. The native settings object exposes only `IsValid` and `IsActiveWindow`; arbitrary material/environment selection is outside the current contract.
- Ordinary checks: `pytest tests/unit/test_dispersion_diagram.py tests/unit/test_contracts.py -q` — 41 passed.
- Native check: `pytest tests/native/test_dispersion_vs_wavelength_live.py -m zemax --run-zemax -q -s` — 1 passed in 14.93 s.
- Result: 101 BK7G18 samples from 0.400 to 0.800 µm, derivative unit `1/micrometer`; preamble conditions 20 °C and 1 atm. The curve wavelength axis and material labels matched the native refractive-index report.
- Numerical reference: centered differences of `n(lambda)` from the matching `DispersionDiagram` curve at 99 interior nodes. Preset absolute tolerance `5e-5 1/micrometer`; maximum observed error `3.49e-5 1/micrometer`.
- Lifecycle: task succeeded; task-result paging returned requested rows; system settings matched before and after; close and stdio disconnect succeeded.
- Raw current run: `.local/runs/runs/dispersion_vs_wavelength_native_c2d2a1c0af/calls.json` and `checks.json`.
