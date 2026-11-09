# Source Polar Viewer Native Probe

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. Input was the installed NSC Colorimetry two-color sample. `SourcePolarViewer` returned valid `AS_Default` / `AR_Default`, one 19x19 grid, no messages/series/scatter collections, and `GetTextFile=false`. The grid range was 0 to 18, with `Dx=10`, `Dy=18.94736842105263`, `MinX=MinY=0`; X, Y, and value labels were all `None`. The analysis object closed and the session disconnected.

Raw grid values and session data: `.local/evidence/development/NS-03/source-polar-20261108/summary.json`. A repeat on 2026-11-08 using the explicit Colorimetry sample reconfirmed NonSequential mode, a 19x19 grid, range 0–18, `Dx=10`, `Dy=18.94736842105263`, zero minima, and `None` for all three labels. Text export remained false; analysis close and disconnect passed. Repeat record: `.local/evidence/development/NS-03/source-polar-repeat-20261108/summary.json`.

The matrix is retained as raw native data without assigning unverified radial/angular semantics. Resume when official axis mapping and units are identified, then compare against a controlled directional source.
