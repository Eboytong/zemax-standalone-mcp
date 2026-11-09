# MA-01.AthermalGlassMap Acceptance

- Environment: OpticStudio 24.2.0 build 240529 PremiumEdition, Python 3.14.
- Scope implemented: typed kind-only `run_analysis` request for the current system wavelength range and all glasses present in the native report. The native setting object is `AS_Default`; only `IsValid` and `IsActiveWindow` are exposed. No material filter or custom axis-bound setting is claimed.
- Native call: `.local/runs/runs/athermal_glass_map_native_2a8eae1915/calls.json`; task result JSON is alongside the session working files.
- Actual condition: minimum/center/maximum wavelength all 0.55 µm. Native report contained 364 glass rows; first row BK7G18 reported chromatic power 0.00000 at xE-3 and thermal power -1.65 at xE-6. The adapter preserves those display values and returns the scaled coordinates.
- Native result: task succeeded; 364 rows and scatter points were returned. Page readback returned 3 of 364 rows. PNG export succeeded. System settings matched before and after. Task close was attempted and stdio disconnect succeeded.
- Ordinary checks: `pytest tests/unit/test_glass_map.py -q` — 12 passed, including request round trip, row/scatter conversion, wavelength parsing, malformed headers, non-finite values, and invalid wavelengths.
- Native check: `pytest tests/native/test_athermal_glass_map_live.py -m zemax --run-zemax -q -s` — 1 passed.
- Native text and exact outlet conditions are retained in `.local/runs/runs/athermal_glass_map_native_2a8eae1915/`.
- Source: the installed 2024 R2 manual describes the map as chromatic and thermal power for current system wavelengths and loaded glass catalogs; the report's native header supplies display scaling. Numerical values are native report values; an independent thermal-power formula comparison remains a follow-up if the declared scope expands beyond the native report adapter.
