# PartViewer Native Repeat

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14.

Two NSC inputs were checked with the isolated `PartViewer` native analysis. The two-color Colorimetry sample had no Part geometry; the Boolean Example 4 Lens Mount contained a RectangularVolume, three CylinderVolumes, a BooleanNative and a NullObject. On the Lens Mount input, `AS_Default` and `AR_Default` were valid and active, but all structured data counts were zero and `GetTextFile` returned false. The native result did not identify or group the part geometry. Both tasks closed and both MCP sessions disconnected normally.

Raw evidence: `.local/evidence/development/NS-03/part-viewer-repeat-20261108/summary.json` and `.local/evidence/development/NS-03/part-viewer-lens-mount-20261108/summary.json`.

The completed check rules out the first sample's missing part geometry as the only cause. Completion still requires a documented part selection/readback contract and usable part data or image/vector result outlet.
