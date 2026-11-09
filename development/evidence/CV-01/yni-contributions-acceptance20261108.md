# YNI Contributions Acceptance

## Scope and environment

`CV-01.YNIContributions`, source version 0.1.61 with the current worktree changes, OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. Input was the installed `Cooke 40 degree field.zos` sample, opened as a task-owned working copy in Sequential mode, configuration 1.

## Native interface and execution

The installed enum is `YNIContributions`. `GetSettings()` returned `AS_Default` with `IsValid=true` and `IsActiveWindow=true`; it exposes no topic-specific settings, so the typed request contains only `kind`. The native result object was valid. Native text export succeeded and contained wavelength 0.55000 µm, millimeter units, and six surface contributions. Result arrays on `AR_Default` were empty, so the implementation parses the native text artifact.

## Result checks

The parsed rows were surfaces 1–6 with YNI values `1.13566`, `-0.74972`, `-1.22579`, `1.00110`, `0.53408`, `-1.40214`. The live stdio test compared each parsed value to the native report at `atol=1e-12`, `rtol=0`; all six passed. The response also exposes these rows through standard pagination and a series curve. Native text is retained as an artifact.

## Lifecycle and checks

The direct outlet probe completed the analysis, closed the native object, and disconnected successfully. The stdio acceptance completed and disconnected successfully. Targeted checks: 5 unit cases and 1 native case passed. Raw probe: `.local/evidence/development/CV-01/yni-outlet-20261108/summary.json`; stdio calls/checks: `.local/runs/runs/yni_contributions_*/`.

## Conclusion

The YNI contribution report is implemented and accepted for the Cooke sample conditions. The exposed contract reports the native-selected wavelength; no wavelength selector is asserted because the installed interface exposes none.
