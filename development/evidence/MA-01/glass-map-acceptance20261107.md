# MA-01.GlassMap: acceptance record

Date: 2026-11-07. Source version: 0.1.61. Native application: OpticStudio 24.2.0 Build 240529, Premium Edition. Python: 3.14.

## Scope and native result

Request: `run_analysis({"request":{"kind":"glass_map"}})`. The native `GlassMap` settings object is `AS_Default`, with actual `IsValid=true` and `IsActiveWindow=true`. The system used the loaded `SCHOTT` catalog. The report contains 346 glass rows with native material name, refractive index `Nd`, and Abbe number `Vd`; the adapter returns page-able `rows` plus scatter points with Abbe number X and refractive index Y. Native convention reverses the X direction for display.

## Reference and lifecycle

The `N-BK7` point was compared with `Documents/Zemax/Glasscat/SCHOTT.AGF`: `Nd=1.51680` and `Vd=64.17`. Both matched the native report at its displayed precision (`Nd` absolute tolerance `5e-6`; `Vd` absolute tolerance `0.005`). Native stdio run passed 1 test; focused ordinary tests passed 51. The test verifies 346 points, paged rows, exported scatter PNG, unchanged system settings, successful task state and normal disconnect.

Commands:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests\unit\test_glass_map.py tests\unit\test_dispersion_diagram.py tests\unit\test_contracts.py tests\unit\test_plotting_units.py -q
.\.venv\Scripts\python.exe -B -m pytest tests\native\test_glass_map_live.py -q --run-zemax
```

Latest native call record: `.local/runs/runs/glass_map_native_b74f4f5eda/calls.json`. Initial outlet and raw native text: `.local/evidence/development/MA-01/glass-map-20261107/summary.json`.

The completed interface reads all glass points from currently loaded catalogs. The native settings object has no catalog-bound or axis-range selectors; the actual current catalog selection is preserved in system settings provenance.
