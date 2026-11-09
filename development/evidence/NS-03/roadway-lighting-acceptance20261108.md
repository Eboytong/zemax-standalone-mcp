# Roadway Lighting Native Probe

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. The installed Non-sequential Colorimetry sample `Example 1 Two-color mixing gives white.zos` was used as an exploratory input because the local sample search found no road/roadway lighting model. The topic executed and exported a native report; settings were valid `AS_Default`, with no topic-specific settings exposed. The result contained no structured arrays or native messages.

The report applied defaults including CIE 140-2000, mounting height 10000 lens units, one-sided arrangement, longitudinal spacing 30000, three lanes, 5000 lane width, R1 surface, and ME1 road class. It returned roadway metrics, including average luminance `1.74981e-06`, Uo=0, Ul=0, TI=0, and SR=3.47391. Since the input was not a controlled road-lighting model and settings could not be read back, these values are not a validated analysis result.

The native analysis closed and the session disconnected successfully. Raw evidence: `.local/evidence/development/NS-03/roadway-lighting-20261108/summary.json`; native report is beside it. Resume with a roadway-specific model/source and an official settings interface that permits final-setting readback; then validate photometric coordinates and metrics against the NSC detector reference.

## Repeat probe, 2026-11-08

The topic was rerun on the same installed two-color fluorescence NSC sample. `AS_Default` was valid and active, and the native text export succeeded. The report again used defaults (CIE 140-2000, mounting height 10000 mm, one-sided layout, three lanes, 5000 mm lane width, R1/ME1) and this time reported zero for average luminance, uniformity, threshold increment, and surround ratio; illuminance rows were N/A. Structured arrays remained empty. No dedicated writable/readable settings were exposed. The analysis closed and the MCP session disconnected.

Raw repeat evidence and report: `.local/evidence/development/NS-03/roadway-lighting-repeat-20261108/summary.json` and `photoluminescence.txt`. The sample search found IES-based projector examples but no roadway-specific model. A valid road-lighting input and formal setting readback remain required for metric acceptance.
