# Source Spectrum Viewer Acceptance

## Scope and input

`NS-03.SourceSpectrumViewer`, source checkout based on 0.1.61, OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. Input: installed Non-sequential Colorimetry sample `Example 1 Two-color mixing gives white.zos`, opened in NonSequential mode, configuration 1.

## Native settings and output

The runtime settings were `AS_Default`, with `IsValid=true` and `IsActiveWindow=true`. The result was valid `AR_Default`; numerical arrays were empty, while `GetTextFile` exported a 1,870-byte native report. The report contains the source XYZ input and fitted XYZ values, CRI, CCT, and 20 spectral wavelength/weight pairs.

## Implementation and checks

Added the typed request `{"kind":"source_spectrum_viewer"}` and a parser that returns native text, summary fields, paginated rows, and a series curve. Wavelengths are in micrometers; weights are the native relative weights, dimensionless, with peak 1. The native stdio test verified all 20 rows, endpoints 0.44 and 0.64 µm, peak weight 1, XYZ values `[1,1,1]`, CRI 70.1766, and CCT 5188 K. Targeted ordinary tests (7) and the native test (1) passed. Native analysis close and MCP disconnect passed.

Raw probe: `.local/evidence/development/NS-03/source-spectrum-20261108/summary.json`; stdio evidence: `.local/runs/runs/source_spectrum_*/`.

## Conclusion

Default XYZ-fitting report parsing was accepted. Recovery audit found an identical report in an empty NSC system; aggregate-source attribution is withdrawn. Full input selection/identity remains implemented pending acceptance. The installed interface exposes no per-source selector; this is reflected by the kind-only request.
