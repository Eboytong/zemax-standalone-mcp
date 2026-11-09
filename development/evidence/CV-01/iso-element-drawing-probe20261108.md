# ISOElementDrawing Native Probe

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. Cooke 40 degree field sequential sample opened as a working copy.

The public `AnalysisIDM.ISOElementDrawing` factory created a valid `ZemaxUI.ZOSAPI.Analysis.AS_Default`; only generic `IsValid` and `IsActiveWindow` settings were exposed. The analysis executed with zero messages, series, grids, RGB grids, or scatter points. `GetTextFile` returned false. The native result type exposes no image/file export member. The baseline and post-analysis surface snapshots matched; native task close and MCP disconnect succeeded.

Command: `.venv\Scripts\python.exe scripts/probes/CV-01/iso_element_drawing_probe.py`.

Raw evidence: `.local/evidence/development/CV-01/iso-element-drawing-20261108/summary.json`. Static interface reflection is in `development/evidence/CV-01/runtime071/settings.json`.

The item remains blocked until the installed public API or official integration exposes a meaningful drawing result/image outlet and any applicable selection contract.
