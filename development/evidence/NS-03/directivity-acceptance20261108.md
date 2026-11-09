# Directivity Plot Acceptance

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. The installed Non-sequential Colorimetry sample `Example 1 Two-color mixing gives white.zos` was opened as a working copy in NonSequential mode.

`DirectivityPlot` returned valid `AS_Default` settings and `AR_Default` results. Structured arrays were empty, while native text export succeeded with the IES source identity `sample.ies`, peak intensity 18 cd, total luminous flux 112.81 lm, and one 37-point curve at scan angle 0 degrees. The report's candela values are normalized to a peak of 1.

Added the kind-only `directivity_plot` request and a parser that returns metadata, paginated angle rows, and `series`. The native stdio test verified all five reference angles: -180°=0, -90°=0.5, 0°=1, 90°=0.5, 180°=0. Targeted ordinary tests (8) and the native test (1) passed. Analysis close and session disconnect passed.

Raw probe: `.local/evidence/development/NS-03/directivity-20261108/summary.json`; native text: `.local/evidence/development/NS-03/directivity-20261108/directivity.txt`; stdio evidence: `.local/runs/runs/directivity_plot_*/`.
