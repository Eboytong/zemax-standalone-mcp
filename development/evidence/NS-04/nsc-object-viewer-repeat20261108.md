# NSCObjectViewer Native Repeat

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. Input: installed `Colorimetry/Example 1  Two-color mixing gives white.zos`.

`NSCObjectViewer` created valid and active `AS_Default` settings and valid `AR_Default` results. The native analysis returned zero messages, series, grids, RGB grids, or scatter points; text export returned false. The same working copy's `get_nsc_objects` call returned 5 current NSC objects with native types and per-object attributes. The viewer result did not identify or render a selected object. Native analysis close and MCP disconnect succeeded.

Raw evidence: `.local/evidence/development/NS-03/nsc-object-viewer-repeat-20261108/summary.json`; it contains the object list, input identity, result counts, settings and lifecycle. Existing static/CFG evidence: `development/evidence/NS-04/runtime066/settings.json`, `development/evidence/NS-04/runtime068-sequential/summary.json`, and `development/evidence/NS-04/outlets068/summary.json`.

The general `get_nsc_objects` entry remains usable for current object data. The dedicated native viewer remains incomplete until formal object selection/readback and a graphical result outlet are available.

2026-11-08 evidence review: the saved summary records total=5 (four SourceEllipse and one DetectorColor); the earlier narrative count of 8 was corrected. See the D008 pass report for the extracted input and result records.
