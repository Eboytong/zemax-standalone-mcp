# Matrix Spot repeat, 2026-11-08

- Item: `CV-01.MatrixSpot`; OpticStudio 24.2.0 build 240529 PremiumEdition; Cooke 40 degree field sample with a duplicated configuration.
- Request: `run_analysis(kind=matrix_spot, color_rays_by=Waves)`; the same native session also exercises the configuration-colored sibling as a control.
- Checks: `.venv\\Scripts\\python.exe -m pytest tests/unit/test_configuration_matrix_spot.py -q` passed 8 tests. `.venv\\Scripts\\python.exe -m pytest tests/native/test_configuration_matrix_spot_live.py -q --run-zemax` passed 1 test.
- Native outcome: MatrixSpot completed its native calculation, but `SpotData` and all inspected data arrays were empty and `GetTextFile` returned false; the MCP task reports the explicit `EXPORT_FAILED` result limitation. The test confirmed task closure and unchanged system settings/surface state for both matrix topics.
- Conclusion: typed request, native execution, error reporting, and lifecycle are checked. Numerical result and independent reference remain unavailable; keep `implemented` pending a formal outlet or validated equivalent calculation.
- Completion count: 0.
