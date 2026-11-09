# Polarization Transmission Native Probe

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. The installed Cooke 40 degree field sample was used. `Transmission` returned valid `AS_Default`/`AR_Default` objects, no structured arrays/messages, and a native text report; the analysis closed and the session disconnected.

The report states an unpolarized field, 32x32 pupil grid, and inclusion of aperture, Fresnel, coatings, vignetting, and internal transmission. It gives total transmission by three fields (0°, 14°, 20°) and wavelengths (0.48, 0.55, 0.65 µm), plus chief-ray per-surface total/relative transmission. Center-field total transmissions are 0.946229361, 0.960700280, and 0.942203090; overall 0.950556246. No topic-specific selector is exposed in `AS_Default`, so the output is limited to the native default unpolarized analysis.

Raw evidence: `.local/evidence/development/NS-03/polarization-transmission-20261108/summary.json`; report is stored beside it. A controlled Fresnel/detector comparison and typed selection contract remain to be established.

## Repeat probe, 2026-11-08

The Cooke sample was rerun from a working copy. The native text report again specified an unpolarized 32×32 pupil grid and included aperture, Fresnel, coating, vignetting, and internal-transmission effects. It reported three fields (0, 14, and 20 degrees), wavelengths 0.480, 0.550, and 0.650 µm, and total field transmissions 0.950556246, 0.949305810, and 0.945339491. Per-surface chief-ray transmission tables were present. `AS_Default` exposed only validity/activity. The analysis closed and the session disconnected normally.

Raw repeat evidence: `.local/evidence/development/NS-03/polarization-transmission-repeat-20261108/summary.json`; report: `.local/evidence/development/NS-03/polarization-transmission-repeat-20261108/photoluminescence.txt`.
