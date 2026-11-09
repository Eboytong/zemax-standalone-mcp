# Radiant Source Model Viewer Native Probe

OpticStudio 24.2.0 Build 240529, local license `PremiumEdition`, Python 3.14. Runtime analysis creation succeeded on the installed NSC Colorimetry two-color sample. Settings were valid `AS_Default`; the result was valid `AR_Default` with one native message and no data series, grids, or scatter data. Text export returned false. The native message was: “只有 OpticStudio 旗舰版支持所需功能。” (“Only the flagship edition of OpticStudio supports the required functionality.”)

The analysis object closed and the session disconnected successfully. A recursive sample/resource search found no dedicated Radiant source-model file in the installed sample tree. Existing IES files do not establish the required Radiant input contract. Raw probe: `.local/evidence/development/NS-03/radiant-viewer-20261108-02/summary.json`.

Resume when an OpticStudio flagship/Enterprise license and a matching Radiant source-model input are available, then verify settings adoption and a nonempty result.

## Repeat probe, 2026-11-08

The topic was rerun on the installed `Fluorescence Example using Waveshift.zos` NSC sample. `AS_Default` and `AR_Default` were valid, with `IsActiveWindow=true`; the native message again stated “只有OpticStudio旗舰版支持所需功能。” No series, grids, scatter data, or text export were available. The task closed and the MCP session disconnected successfully. The configured local edition remains PremiumEdition.

Raw repeat evidence: `.local/evidence/development/NS-03/radiant-viewer-repeat-20261108/summary.json`. The completion conditions remain a flagship/Enterprise license and a matching Radiant source-model input with a valid result.
