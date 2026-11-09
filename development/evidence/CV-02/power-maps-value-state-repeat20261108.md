# Power Map Value-State and Aperture-Ring Repeat

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14.

Checks run:

- `.venv\Scripts\python.exe -m pytest tests/unit/test_power_maps.py -q`: 27 passed.
- `.venv\Scripts\python.exe -m pytest tests/native/test_power_map_value_states_live.py -q --run-zemax`: 1 passed in 22.60 s.
- `.venv\Scripts\python.exe -m pytest tests/native/test_power_map_aperture_ring_live.py -q --run-zemax`: 1 passed in 29.17 s.

Both `power_field_map` and `power_pupil_map` were exercised for Power/EFL on planar and R50 N-BK7 surfaces. The tests confirmed native zero preservation under a +7 output offset, finite nonzero reference values, row and region pagination, task success without cleanup warnings, and model/system/merit preservation through save/reload. Shrinking the clear aperture to 0.1, 0.001, and 0.00001 mm did not expose native peripheral ring-validity data; `native_ring_validity` remains `unavailable`. The adapter therefore reports center reference-ray validity and keeps raw zero interpretation explicitly unresolved.

Raw current-run results: `.local/runs/runs/power596_value_states_77609bd128/value-states.json` and `.local/runs/runs/power593_aperture_ring_12774d2086/ring-diagnostic.json`.

This repeat confirms the existing result contract. Formal native ring nodes/validity and zero-EFL semantics remain open for both maps.
