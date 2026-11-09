# DispersionDiagram Current-System Acceptance

- Environment: OpticStudio 24.2.0 build 240529 PremiumEdition, Python 3.14.
- Supported scope: typed kind-only request for the native current-system refractive-index versus wavelength report. Arbitrary material/environment selectors are outside the supported contract because `SettingsFirst/GetSettings` exposes only `IsValid` and `IsActiveWindow`.
- Ordinary checks: `pytest tests/unit/test_dispersion_diagram.py tests/unit/test_contracts.py -q` — 41 passed.
- Native check: `pytest tests/native/test_dispersion_diagram_live.py -m zemax --run-zemax -q -s` — 1 passed in 14.38 s.
- Result: 101 wavelength points for `BK7G18`, 0.400–0.800 µm at 0.004 µm spacing; native preamble reported 20 °C and 1 atm. Refractive index is dimensionless and native displayed digits are retained.
- Lifecycle: analysis task succeeded and emitted native text; first three rows were read through task-result paging; system settings matched before/after; stdio disconnected normally.
- Evidence: `.local/runs/runs/dispersion_diagram_native_f643af389e/calls.json`; previous raw text and initial result record remain referenced by `dispersion-diagram-acceptance20261107.md`.
