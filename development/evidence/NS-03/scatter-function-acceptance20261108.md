# Scatter Function Viewer Native Probe

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. Input was the installed `Non-sequential/Scattering/ABg scattering surface.zos` sample, opened in NonSequential mode. The loaded model was queried before analysis and retained as the input identity.

The runtime settings and result objects were valid (`AS_Default` / `AR_Default`), with no messages, series, grids, RGB grids, or scatter-point collections. `GetTextFile` returned false. The analysis closed and the backend disconnected successfully. Raw probe: `.local/evidence/development/NS-03/scatter-function-20261108/summary.json`.

## Controlled face/settings follow-up

On 2026-11-08 the ABg sample was reopened and `get_nsc_objects` confirmed Rectangle object 2, face 0, `CurrentScatterModel=ABg`, `ReflectName=ABG-EXAMPLE`, `IsValid=true`, and `NumberOfRays=5`. A controlled attempt to set `ScatterFraction=1.0` was rejected because native `IOSS_ABg` has no `ScatterFraction` member (`SETTING_REJECTED`; checkpoint retained). The analysis still returned zero messages/series/grids/scatter points and `GetTextFile=false`. Tool close and session disconnect passed.

Raw repeat: `.local/evidence/development/NS-03/scatter-function-repeat-20261108/summary.json`. Controlled write attempt: `.local/evidence/development/NS-03/scatter-function-active-abg-20261108/summary.json`.

The declaration remains blocked at its formal data outlet. Resume when a supported scattering-function grid/series or image path is exposed.

## Input-contract correction, 2026-11-08

The installed 2024 R2 manual, extracted in `.local/evidence/development/NS-03/manual-index-1393.txt`, defines this library viewer's own Scatter Model, Wavelength, Fraction, Sigma/Angle and File Name/DLL Name selections. Fraction is explicitly ignored for ABg and ABg File. Editing an NSC object face does not establish which model this independent viewer selected. The earlier face readback remains valid evidence for the object, and its rejected ScatterFraction write is not an unmet ABg viewer requirement.

No new native run was needed for this correction. Existing AS_Default reflection exposes no viewer-specific setters/readback, and the prior execution still has no usable output. Resume with a formal viewer model/resource selector and adopted-value identity, followed by a nonempty series/grid/image outlet and an independent BSDF reference. Current state stays blocked; batch count unchanged.
