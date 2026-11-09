# Polarization Ray Trace Native Probe

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. The installed Cooke 40 degree field sample was opened as a working copy. `PolarizationRayTrace` returned valid `AS_Default` settings and valid `AR_Default` results. Structured arrays were empty; the native text export succeeded.

The report identifies 0.55 µm, center field, normalized pupil `(Px=0, Py=1)`, input polarization `(Jx=0, Jy=1)` and phase 0. It includes local surface coordinates/directions, path length, phase factor, complex E-field components, coating `Rs/Rp/Ts/Tp`, complex reflection/transmission amplitudes and phase delays with degree equivalents. The analysis closed and the session disconnected.

Raw evidence: `.local/evidence/development/NS-03/polarization-ray-trace-20261108/summary.json`; native report is stored beside it. `AS_Default` exposes no topic-specific selectors, so the captured run verifies only the default ray and polarization state. A typed input contract and independent Fresnel check remain open.

## Repeat probe, 2026-11-08

The Cooke 40 degree field sample was rerun from a working copy. Native text export succeeded. The default ray was at normalized field `(0,0)`, pupil `(0,1)`, wavelength `0.550000000 µm`, with input Jones field `X=0, Y=1` and zero phase. The report includes local-coordinate directions, surface-normal and s/p basis vectors, complex E-field, intensity, reflection coefficients, and propagation phase. `AS_Default` exposes only validity/activity, so the ray/polarization selectors remain unavailable. The analysis closed and the session disconnected normally.

Raw repeat evidence: `.local/evidence/development/NS-03/polarization-ray-trace-repeat-20261108/summary.json`; report: `.local/evidence/development/NS-03/polarization-ray-trace-repeat-20261108/photoluminescence.txt`.
