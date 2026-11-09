# Photoluminescence Viewer Native Probe

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. Two installed NSC samples were tested serially: `Fluorescence Example using Waveshift.zos` and `White LED Phosphor.zos`.

Both `PhotoluminscenceViewer` analyses created valid `AS_Default` settings and valid `AR_Default` results. Each result contained one native message, zero series/grids/scatter collections, and a text report stating “输入无效数据/设置” (“invalid input data/settings”). The first sample had no PhotoluminescenceModel volume; the second included one on object 3, but the topic still rejected the input. The analysis objects closed and both MCP sessions disconnected successfully. The local Premium license allowed the topic to be created and executed.

Raw evidence: `.local/evidence/development/NS-03/photoluminescence-20261108/summary.json` and `.local/evidence/development/NS-03/photoluminescence-20261108-white-led-phosphor/summary.json`.

The complete topic remains blocked until a documented input/selection contract or valid model requirements are obtained for this analysis, followed by a nonempty output and a reference condition.

## Repeat probe, 2026-11-08

The `Fluorescence Example using Waveshift.zos` sample was rerun after the workstation restart. The native analysis again returned the message “输入无效数据/设置”, with an empty result collection and a 30-byte text export. The model contained SourceEllipse, scattering, beam-splitter, and two DetectorColor objects. The analysis and control resources closed, and the MCP session disconnected normally.

Raw repeat evidence: `.local/evidence/development/NS-03/photoluminescence-repeat-20261108/summary.json`. This confirms the earlier result; the input contract and a valid output/reference remain the specific completion conditions.
