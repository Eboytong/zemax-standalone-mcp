# PrescriptionGraphic Runtime Probe

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14.

Two modes were tested independently:

- Sequential Cooke 40 degree field sample: factory returned valid `AS_Default`/`AR_Default`, all structured data counts were zero, and `GetTextFile` returned false. Analysis close and MCP disconnect succeeded.
- Pure NSC two-color Colorimetry sample: `New_Analysis_SettingsFirst(AnalysisIDM.PrescriptionGraphic)` returned null. The probe's subsequent `GetSettings` raised `AttributeError: 'NoneType' object has no attribute 'GetSettings'`. No analysis object was created; MCP disconnect succeeded.

Raw evidence: `.local/evidence/development/NS-03/prescription-graphic-sequential-20261108/summary.json` and `.local/evidence/development/NS-03/prescription-graphic-nsc-20261108/summary.json`.

The sequential result has no usable graphic/text outlet, and the pure NSC factory is unavailable. Completion requires a formal sequential graphic export path and a supported NSC factory if that mode belongs to the declared scope.
