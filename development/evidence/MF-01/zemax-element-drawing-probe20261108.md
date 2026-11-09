# ZemaxElementDrawing Native Probe

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. Cooke 40 degree field sequential sample.

The isolated native probe created valid `ZemaxUI.ZOSAPI.Analysis.AS_Default` settings with only generic properties; `IsActiveWindow=false`. The analysis returned zero messages, series, grids, RGB grids, scatter points, and ray data. Text export returned false. Neither settings nor result interfaces exposed a drawing/image/vector outlet. The analysis closed and the MCP session disconnected normally.

Command: `.venv\Scripts\python.exe scripts/probes/MF-01/manufacturing_viewer_probe.py .local/evidence/development/MF-01/zemax-element-drawing-repeat-20261108 --topic ZemaxElementDrawing`.

Raw evidence: `.local/evidence/development/MF-01/zemax-element-drawing-repeat-20261108/probe.json`; prior static/runtime reflection: `development/evidence/MF-01/runtime078/settings.json` and `development/evidence/MF-01/probe427-viewers/probe.json`.

Completion requires a formal native drawing result or image/vector export contract, plus an input-to-drawing identity check.
