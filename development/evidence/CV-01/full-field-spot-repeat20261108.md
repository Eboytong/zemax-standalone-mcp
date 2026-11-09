# Full-field Spot repeat, 2026-11-08

- Item: `CV-01.FullFieldSpot`; source version 0.1.61 worktree; OpticStudio 24.2.0 build 240529 PremiumEdition; Cooke 40 degree field sample.
- Requests exercised: `(field=1,wavelength=1,Centroid,exaggerate=1)`, `(field=0,wavelength=0,Centroid,exaggerate=1)`, and `(field=1,wavelength=1,ChiefRay,exaggerate=3)`.
- Ordinary checks: `.venv\\Scripts\\python.exe -m pytest tests/unit/test_full_field_spot.py -q` passed 13 tests, including request bounds, settings readback, units, invalid native values, and empty-outlet error reporting.
- Native check: `.venv\\Scripts\\python.exe -m pytest tests/native/test_full_field_spot_live.py -q --run-zemax` passed 1 scenario. All three settings variants reported `RESULT_UNAVAILABLE` because SpotData and every formal data outlet were empty; task closure was confirmed for each. The native test also compares system surfaces to the baseline after each failed request and passed.
- Conclusion: settings/execution/error/lifecycle behavior is covered; no full-field numerical output is available to compare against standard spot results. Keep the item `implemented` pending a valid native outlet or validated equivalent reference/scale/layout mapping.
- Completion count: 0.
