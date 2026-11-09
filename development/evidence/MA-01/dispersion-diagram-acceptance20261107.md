# MA-01.DispersionDiagram: acceptance record

Date: 2026-11-07. Source version: 0.1.61. Native application: OpticStudio 24.2.0 Build 240529, Premium Edition. Python: 3.14.

## Request and native adoption

Request: `run_analysis({"request":{"kind":"dispersion_diagram"}})`. The typed request has no selectors because the runtime `SettingsFirst`/`GetSettings` object exposes only `IsValid=true` and `IsActiveWindow=true`. The native report selected material column `BK7G18`; its preamble reported 20.0000 C and 1.0000 atm. The current-system report scope is supported. Selecting arbitrary material columns or environmental conditions remains unresolved.

## Result and checks

The native text outlet returned 101 points from 0.400 to 0.800 micrometers at 0.004 micrometer spacing. The curve reports refractive index as dimensionless and preserves the native material label and displayed digits. The native text is retained as an artifact. Request parsing, multiple material columns, environment parsing, invalid titles, missing headers, nonmonotonic axes and invalid values are covered by the ordinary tests.

Commands:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests\unit\test_dispersion_diagram.py -q
.\.venv\Scripts\python.exe -B -m pytest tests\native\test_dispersion_diagram_live.py -q --run-zemax
```

Results: the focused ordinary run covering the parser, MCP contracts, and existing analysis adapters passed 65 tests; the final native stdio run passed 1 test. The native session completed the task successfully, verified the `BK7G18` label, 101 points, 20 C / 1 atm, read the first three curve rows through task-result paging, retained identical system settings, and disconnected normally. Latest native call record: `.local/runs/runs/dispersion_diagram_native_1d02f582d7/calls.json`. Earlier full outlet evidence, including raw text and disconnect state: `.local/evidence/development/MA-01/dispersion-diagram-20261107/summary.json`.

## Remaining work

Ledger status was initially blocked pending scope confirmation. On 2026-11-08 the declared supported scope was set to the native current-system report; arbitrary material/environment selection remains an extension condition. Current native recheck: `development/evidence/MA-01/dispersion-diagram-current-system-20261108.md`.
