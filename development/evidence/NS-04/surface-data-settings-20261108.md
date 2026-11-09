# SurfaceDataSettings Native Check

- Environment: OpticStudio 24.2.0 build 240529 PremiumEdition, Python 3.14.
- Plan: rerun the sequential report, inspect settings, identify reported surface and units, and record task/resource closure.
- Command: `\.venv\Scripts\python.exe -B scripts\probes\BASE-01\report_outlet_probe068.py --output .local\evidence\development\NS-04\surface-20261108 --mode Sequential --items SurfaceDataSettings`.
- Result: one analysis completed; task `80c79fad920a4e9e9f337b10a6b9aa9f` succeeded. Settings were `IsValid=true`, `IsActiveWindow=true`.
- Output: 938-byte native text report titled “表面 1 数据概要”; it reports surface 1, lens unit millimeters, thickness/diameter/edge thickness, refractive index at 0.55 µm, and surface power.
- Lifecycle: task `close_attempted=true`; backend disconnect returned `ok=true`.
- Selection contract: the default object exposed no surface selector or adopted surface identity. The report therefore verifies a default single-surface result only.
- Status: blocked for selectable surface reporting. Unlock when a formal surface selector and reliable adopted surface readback are available.
- Raw run: `.local/evidence/development/NS-04/surface-20261108/summary.json` and referenced native text file.
