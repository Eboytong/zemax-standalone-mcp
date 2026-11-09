# Source Illumination Map Native Probe

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. Input was the installed Non-sequential Colorimetry two-color sample in NonSequential mode. `SourceIlluminationMap` returned valid `AS_Default` and `AR_Default`, with zero messages, series, grids, RGB grids, or scatter collections. Native text export returned false. The analysis object closed and the session disconnected successfully.

The two-color sample was repeated on 2026-11-08 with an explicit `Colorimetry` sample path. `get_nsc_objects` confirmed four `SourceEllipse` objects using system wavelengths 1/2 at 1 W each and a `DetectorColor` object. `SourceIlluminationMap` again returned valid AS_Default/AR_Default with no messages, series, grids, RGB grids, or scatter points; `GetTextFile=false`. Analysis close and session disconnect passed.

Raw repeat evidence: `.local/evidence/development/NS-03/source-illumination-twocolor-20261108/summary.json`. The source condition is confirmed; the remaining blocker is the absent supported illumination grid/image outlet. Resume when that result path is exposed, then validate coordinates, units, and flux against the detector.
