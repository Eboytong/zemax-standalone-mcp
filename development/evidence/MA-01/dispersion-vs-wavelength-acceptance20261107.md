# MA-01.DispersionvsWavelength: acceptance record

Date: 2026-11-07. Source version: 0.1.61. Native application: OpticStudio 24.2.0 Build 240529, Premium Edition. Python: 3.14.

## Native interface and result

Request: `run_analysis({"request":{"kind":"dispersion_vs_wavelength"}})`. The native `DispersionvsWavelength` settings object exposes `IsValid=true` and `IsActiveWindow=true`. The analysis produced a native text table titled `色散 vs. 波长`, with wavelength in `µm` and derivative in `1/um`; it contains 101 `BK7G18` samples from 0.400 to 0.800 µm. The report preamble gives 20 C and 1 atm. The adapter retains the native text and returns the derivative in `1/micrometer`.

## Numerical reference and lifecycle

The reference is the centered finite difference of the native `DispersionDiagram` refractive-index curve at matching wavelengths:

```text
(n[i+1] - n[i-1]) / (wavelength[i+1] - wavelength[i-1])
```

Predeclared absolute tolerance: `5e-5 1/micrometer`, accounting for seven-decimal native text values and finite-difference truncation. All 99 interior samples passed; maximum absolute difference was `3.49e-5 1/micrometer`. Ordinary tests covering parsing, MCP contracts and existing adapters: 70 passed. Native stdio test: 1 passed. It verified task success, settings validity, material/condition identity, task-result paging, unchanged system settings and normal disconnect.

Commands:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests\unit\test_dispersion_diagram.py tests\unit\test_contracts.py tests\unit\test_remaining_adapters.py -q
.\.venv\Scripts\python.exe -B -m pytest tests\native\test_dispersion_vs_wavelength_live.py -q --run-zemax
```

Evidence: `.local/evidence/development/MA-01/dispersion-vs-wavelength-20261107/summary.json` and `.local/runs/runs/dispersion_vs_wavelength_native_a25e0a1765/calls.json`.

## Remaining work

The runtime settings object has no writable material or environmental selector. On 2026-11-08, the supported contract was defined as the native current-system derivative report. Arbitrary selectors remain a future extension. The rerun and scope evidence is in `development/evidence/MA-01/dispersion-vs-wavelength-current-system-20261108.md`.
