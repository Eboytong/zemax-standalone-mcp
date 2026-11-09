# PrescriptionDataSettings Native Check

- Environment: OpticStudio 24.2.0 build 240529 PremiumEdition, Python 3.14.
- Plan: rerun the sequential default report, inspect settings, task/result artifacts, and lifecycle, then assess whether a typed section selector is available.
- Command: `\.venv\Scripts\python.exe -B scripts\probes\BASE-01\report_outlet_probe068.py --output .local\evidence\development\NS-04\prescription-20261108 --mode Sequential --items PrescriptionDataSettings`.
- Result: 1 native analysis executed; task `68ace1bed8d14c1cb569d97dbc5bfb09` succeeded, progress 100, elapsed 0.248 s. `AS_Default` returned `IsValid=true`, `IsActiveWindow=true`.
- Output: native text and task JSON were written under `.local/evidence/development/NS-04/prescription-20261108/native/87f78e6437c045a3af07ba73ec433e30/`. The report begins with system/detailed data and contains prescription sections.
- Lifecycle: `close_attempted=true`; the analysis task reached succeeded and the backend disconnect returned `ok=true`.
- Setting contract: no section selection or adopted section identity is exposed by the settings object or current reflected interface evidence. The result is the native default report, not a selectable-section implementation.
- Status: blocked for the declared typed section-selection scope. Unlock when official `ModifySettings` keys or a dedicated settings interface and reliable selection readback are found. The default report export remains available through the native task path.
