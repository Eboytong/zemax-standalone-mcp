# SagTable Statistics and Applicability Repeat

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14.

Checks run:

- `.venv\Scripts\python.exe -m pytest tests/unit/test_sag_table.py -q`: 38 passed.
- `.venv\Scripts\python.exe -m pytest tests/native/test_sag_table_statistics_live.py -q --run-zemax`: 3 passed in 53.43 s.
- `.venv\Scripts\python.exe -m pytest tests/native/test_sag_table_applicability_live.py -q --run-zemax`: 3 passed in 51.86 s.

The slope-summary tests used positive/negative EvenAspheric terms and a 1 mm inner radius. Native reports exposed 1000 intervals/1001 nodes. Independent analytic sag/slope and radial-area references passed for maximum/RMS slope difference, removal depth, and removal volume at the tolerances stored by each test. Task close, system settings, merit function, and surface state checks passed.

Applicability checks rejected an anisotropic Biconic, accepted an equal-radii rotational Biconic as a sphere with 24 meridian samples agreeing, and showed that a decentered circular clear aperture does not change the SagTable full-blank radial range. Existing native coverage also includes signed plane/sphere/concave surfaces, annular requests, paging, cancellation, image export, reuse, and reload.

This work does not establish a manufacturing-offset input/reference contract or a reverse-manufacturing summary. Those remain the precise open conditions; the native settings interface does not expose an adopted offset selection.

Raw repeat runs: `.local/runs/runs/sag518_statistics_*/` and `.local/runs/runs/sag553_biconic_applicability_*/`.
