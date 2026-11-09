# SeidelDiagram Native Repeat

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14, Cooke 40 degree field sample.

Checks run:

- `.venv\Scripts\python.exe -m pytest tests/unit/test_seidel_diagram.py -q`: 5 passed.
- `.venv\Scripts\python.exe -m pytest 'tests/native/test_seidel_slopes_live.py::test_seidel_slopes_native_settings_results_and_close[seidel_diagram]' -q --run-zemax`: 1 passed in 13.82 s after aligning the test with the explicit native output limitation.
- `.venv\Scripts\python.exe -m pytest tests/native/test_basic_analyses_live.py -q --run-zemax`: 1 passed in 19.61 s.

Seidel Diagram settings were read back as `IgnoreChromatic=false`, `IgnoreDistortion=false`, `SuppressFrame=false`, `PlotScale=0`, with valid active settings. Native text export failed with `EXPORT_FAILED`, no artifacts were returned, and `close_attempted=true`. The revised test now treats that known native outlet limitation as the expected result while checking settings and cleanup.

The separate `SeidelCoefficients` analysis returned numerical rows and passed its independent spherical S1 reference at absolute tolerance `1e-6`. This does not provide the missing diagram plot. Raw run directories: `.local/runs/runs/seidel_diagram_dbed395647/` and `.local/runs/runs/basic_analyses_validation_*/`.

The diagram remains blocked until the native API provides a graphical/numerical SeidelDiagram result outlet; coefficient analysis remains separately usable.
