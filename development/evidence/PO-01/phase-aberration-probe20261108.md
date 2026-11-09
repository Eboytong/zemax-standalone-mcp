# Phase Aberration Native Probe

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. The installed Cooke 40 degree field sequential sample was opened as a working copy. `PhaseAberration` returned valid `AS_Default` settings and a valid `AR_Default` result; structured arrays were empty, but native text export succeeded (48,976 bytes).

The report identifies 0.5500 µm, field position 0.00 degrees, `Jx=0`, `Jy=1`, input X/Y phase 0. It contains 201 pupil-coordinate samples in each of sagittal and tangential sections, with X/Y phase values. The report does not label the phase unit, and the settings interface exposes no topic-specific writable properties. The analysis closed and the session disconnected.

Raw evidence: `.local/evidence/development/NS-03/phase-aberration-20261108/summary.json`; report: `.local/evidence/development/NS-03/phase-aberration-20261108/photoluminescence.txt`.

The result outlet is available, but typed selectors, actual setting adoption and phase-unit semantics remain open. Resume when the installed API or formal documentation establishes those contracts and an independent phase reference can be fixed.

## Repeat probe, 2026-11-08

The Cooke 40 degree field sample was rerun from a working copy. The text export again succeeded and identified 0.5500 µm, field position 0.00 degrees, `Jx=0`, `Jy=1`, and zero input X/Y phase. It returned 201 pupil-coordinate samples for both sagittal and tangential sections; the first listed Y-phase values were `-0.011767056` and `-0.011626575`. The report still does not state a phase unit, and `AS_Default` exposes only validity/activity. The task closed and the session disconnected normally.

Raw repeat evidence: `.local/evidence/development/NS-03/phase-aberration-repeat-20261108/summary.json`; report: `.local/evidence/development/NS-03/phase-aberration-repeat-20261108/photoluminescence.txt`.

## Source parser replay, 2026-11-08

The integrated parser replayed the original retained report and read **401 pupil rows**, with both sagittal and tangential X/Y values in each row, producing four series. The earlier 201-point count above was a manual counting error. The replay receipt is `.local/evidence/development/BASE-04/parallel-01/polarization-retained-replay.json`; the raw reports are preserved. Phase is declared in waves from the manual definition and remains unverified against the independent native complex-field reference.
