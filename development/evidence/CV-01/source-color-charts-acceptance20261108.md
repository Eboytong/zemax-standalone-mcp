# Source Color Chart Native Outlet Probe

## Scope

`CV-01.SourceColorChart1931` and `CV-01.SourceColorChart1976`, OpticStudio 24.2.0 Build 240529, PremiumEdition, Sequential mode, configuration 1, Millimeters. Probe ran on 2026-11-08 from the source checkout with Python 3.14.

## Request and settings

Each native analysis was created through `new_analysis` and read back before execution. Both returned `ZemaxUI.ZOSAPI.Analysis.AS_Default` with `IsValid=true` and `IsActiveWindow=true`; no topic-specific settings were exposed by the returned object. The probe invoked `ApplyAndWaitForCompletion` for each analysis in sequence.

## Results

Both `GetResults()` calls returned `ZemaxUI.ZOSAPI.Analysis.AR_Default`, `IsValid=true`, zero messages, zero data series, zero data grids, zero RGB grids, and zero scatter-point collections. `GetTextFile` returned false for both. No image or numerical payload was available through the inspected public result object. Both analysis objects were closed through the project native close helper and the backend disconnected successfully. Session identifiers and exact raw properties/methods are retained in `.local/evidence/development/CV-01/source-color-outlets-20261108-02/summary.json`.

## Follow-up across model modes

The official 2024 R2 help classifies both analyses as fixed CIE reference charts; their definitions do not depend on an optical system or source image. Reruns used both the two-color NSC Colorimetry sample and the Cooke sequential sample. In both modes each analysis was created, returned valid `AS_Default` and `AR_Default` objects, executed, then returned zero messages, series, grids, RGB grids, scatter collections and text output. Analysis close and session disconnect succeeded in all runs. Records are `.local/evidence/development/CV-01/source-color-nsc-1931-20261108/summary.json`, `source-color-nsc-1976-20261108/summary.json`, and `source-color-sequential-1931-20261108/summary.json`.

## Conclusion and next action

Both items remain blocked because OpticStudio 2024 R2 exposes no chart pixels or coordinates through the inspected `AR_Default` result, and `GetTextFile` returns false. The source-image-selector condition has been removed. Resume when a supported GUI/image capture/export route or another official chart-data outlet is available; alternatively, use a documented and independently validated CIE locus source whose identity and precision are retained.
