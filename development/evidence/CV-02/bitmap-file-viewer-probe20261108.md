# BitmapFileViewer Native Probe

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. Cooke 40 degree field sequential sample.

The isolated `BitmapFileViewer` probe created `ZemaxUI.ZOSAPI.Analysis.AS_Default`; only generic validity and active-window properties were exposed, with `IsActiveWindow=false`. The analysis executed with zero messages, data series, grids, RGB grids, scatter points, or ray data. `GetTextFile` returned false and no image-selection/result method was present. Native close and MCP disconnect succeeded.

Command: `.venv\Scripts\python.exe scripts/probes/MF-01/manufacturing_viewer_probe.py .local/evidence/development/CV-02/bitmap-viewer-repeat-20261108 --topic BitmapFileViewer`.

The local `read_bitmap` adapter's 8 tests passed: `.venv\Scripts\python.exe -m pytest tests/unit/test_native_bitmap.py -q`. It validates owned BMP parsing and PNG export, but does not replace the missing native viewer file-selection contract.

Raw reflection/run: `.local/evidence/development/CV-02/bitmap-viewer-repeat-20261108/probe.json`.

Completion requires a formal bitmap file selector/readback and an image or pixel result outlet.
